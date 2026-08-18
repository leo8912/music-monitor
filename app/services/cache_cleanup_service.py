# -*- coding: utf-8 -*-
"""
CacheCleanupService - 音频缓存自动清理

职责:
- 清理 cache_dir 下的"孤儿文件" (DB 无 Song 记录指向的文件: 下载残留、
  中断遗留、已被忽略后残留等)
- 缓存总大小超过 max_cache_size * cleanup_threshold 时, 按文件修改时间
  从旧到新继续清理孤儿文件, 直到低于阈值
- 超过 retention_days 的孤儿文件优先清理

安全边界 (绝不自动删除):
- **待定歌曲**: DB 有 Song 记录且 local_path 位于 cache_dir 内的文件
  (即「待定」列表的数据源, 只有用户显式忽略才会删除)
- 已收藏 (favorites_dir) / 已入库 (library_dir) 的文件天然不在 cache_dir 内

配置 (config.yaml storage 段):
  auto_cache_enabled: 总开关 (默认 true)
  max_cache_size:     容量上限 (字节, 默认 10GB)
  cleanup_threshold:  触发清理的容量比例 (默认 0.8)
  retention_days:     孤儿文件保留天数 (默认 180)
  cleanup_interval_hours: 定时清理间隔小时数 (默认 24, 供调度器读取)

Author: music-monitor development team
"""
import logging
import os
import time
from typing import Dict, Optional, Set, Tuple

import anyio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.song import Song
from core.config_manager import get_config_manager
from core.storage import StoragePaths

logger = logging.getLogger(__name__)

# 缓存目录内视为音频的扩展名 (与 ScanService 保持一致)
AUDIO_EXTS = (".mp3", ".flac", ".m4a", ".wav", ".aac", ".ogg")


def _norm(path: str) -> str:
    """规范化路径用于集合比较 (Windows 大小写不敏感)。"""
    return os.path.normcase(os.path.abspath(os.path.realpath(path)))


class CacheCleanupService:
    """音频缓存自动清理服务"""

    _instance: Optional["CacheCleanupService"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        pass

    @classmethod
    def get_instance(cls) -> "CacheCleanupService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # 对外入口
    # ------------------------------------------------------------------
    async def cleanup(self, db: AsyncSession) -> Dict:
        """
        执行一次缓存清理。

        Returns:
            {
                "skipped": bool,          # True 表示未启用/无缓存目录, 未执行
                "checked_files": int,     # 扫描到的音频文件数
                "orphan_files": int,      # 孤儿文件数
                "removed_count": int,     # 本次删除的文件数
                "freed_bytes": int,       # 释放的字节数
                "kept_pending": int,      # 保留的待定歌曲数
                "total_bytes": int,       # 清理前缓存总大小
            }
        """
        cfg = get_config_manager().get("storage", {}) or {}
        if not cfg.get("auto_cache_enabled", True):
            logger.info("[CacheCleanup] auto_cache_enabled=false, 跳过清理")
            return {"skipped": True, "removed_count": 0, "freed_bytes": 0}

        max_size = int(cfg.get("max_cache_size", 10 * 1024 ** 3))
        threshold = float(cfg.get("cleanup_threshold", 0.8))
        retention_days = int(cfg.get("retention_days", 180))

        paths = StoragePaths.get_instance()
        cache_dir = paths.cache_dir  # property 会惰性创建
        if not cache_dir.is_dir():
            logger.info("[CacheCleanup] 缓存目录不存在, 跳过")
            return {"skipped": True, "removed_count": 0, "freed_bytes": 0}

        cache_prefix = _norm(str(cache_dir))

        # 1. 收集 DB 中位于 cache 内的有效文件 (待定歌曲, 永不自动删除)
        pending_paths, kept_pending = await self._collect_pending_paths(db, cache_prefix)

        # 快照时间戳: 扫描/删除期间并发下载或入库提交的新文件, 其 mtime 会晚于该时间戳。
        # 这些文件不在 pending_paths 快照中, 若按年龄清理可能误删刚下载/刚入库的文件,
        # 因此扫描时跳过 mtime >= snapshot_ts 的文件 (视为"新文件", 留给下一轮清理)。
        snapshot_ts = time.time()

        # 2. 扫描缓存目录, 区分 孤儿文件 / 有效文件, 统计总大小
        orphans: list[Tuple[float, int, str]] = []  # (mtime, size, path)
        total_bytes = 0
        checked_files = 0
        for root, _dirs, files in await anyio.to_thread.run_sync(
            lambda: list(os.walk(str(cache_dir)))
        ):
            for fname in files:
                if not fname.lower().endswith(AUDIO_EXTS):
                    continue
                fp = os.path.join(root, fname)
                try:
                    st = await anyio.to_thread.run_sync(os.stat, fp)
                except OSError:
                    continue
                if not await anyio.to_thread.run_sync(os.path.isfile, fp):
                    continue
                # 跳过快照之后才出现/修改的文件 (并发下载/入库的新文件)
                if st.st_mtime >= snapshot_ts:
                    continue
                checked_files += 1
                total_bytes += st.st_size
                if _norm(fp) not in pending_paths:
                    orphans.append((st.st_mtime, st.st_size, fp))

        orphans.sort(key=lambda x: x[0])  # 最旧在前
        logger.info(
            f"[CacheCleanup] 扫描完成: 音频 {checked_files} 个, 总 {total_bytes / 1048576:.1f} MB, "
            f"待定保留 {len(pending_paths)} 个, 孤儿 {len(orphans)} 个"
        )

        # 3. 清理超保留期的孤儿
        cutoff = time.time() - retention_days * 86400
        removed = 0
        freed = 0
        remaining: list[Tuple[float, int, str]] = []
        for mtime, size, fp in orphans:
            if mtime < cutoff:
                if await self._remove_file(fp):
                    removed += 1
                    freed += size
            else:
                remaining.append((mtime, size, fp))

        # 4. 容量超限: 从最旧开始继续清理孤儿, 直到低于阈值
        limit = max_size * threshold
        if total_bytes - freed > limit and remaining:
            logger.info(f"[CacheCleanup] 缓存 {total_bytes / 1048576:.1f} MB 超过阈值 {limit / 1048576:.1f} MB, 开始容量清理")
            for mtime, size, fp in remaining:
                if total_bytes - freed <= limit:
                    break
                if await self._remove_file(fp):
                    removed += 1
                    freed += size

        if removed:
            logger.info(f"[CacheCleanup] 完成: 删除 {removed} 个孤儿文件, 释放 {freed / 1048576:.1f} MB")
        else:
            logger.info("[CacheCleanup] 完成: 无孤儿文件需要清理")
        return {
            "skipped": False,
            "checked_files": checked_files,
            "orphan_files": len(orphans),
            "removed_count": removed,
            "freed_bytes": freed,
            "kept_pending": kept_pending,
            "total_bytes": total_bytes,
        }

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------
    async def _collect_pending_paths(self, db: AsyncSession, cache_prefix: str) -> Tuple[Set[str], int]:
        """收集 DB 中 local_path 位于 cache 内的文件路径 (待定歌曲)。"""
        stmt = select(Song.local_path).where(Song.local_path.isnot(None))
        rows = (await db.execute(stmt)).scalars().all()
        pending: Set[str] = set()
        for raw in rows:
            if not raw:
                continue
            norm = _norm(raw)
            if norm.startswith(cache_prefix):
                pending.add(norm)
        return pending, len(pending)

    async def _remove_file(self, path: str) -> bool:
        """删除单个文件, 返回是否成功。"""
        try:
            await anyio.to_thread.run_sync(os.remove, path)
            logger.info(f"[CacheCleanup] 已删除孤儿文件: {path}")
            return True
        except FileNotFoundError:
            return False
        except OSError as e:
            logger.warning(f"[CacheCleanup] 删除失败 {path}: {e}")
            return False


def get_cache_cleanup_service() -> CacheCleanupService:
    """单例入口"""
    return CacheCleanupService.get_instance()
