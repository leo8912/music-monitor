# -*- coding: utf-8 -*-
"""
IgnoreService - 忽略歌曲服务

用户手动「忽略」一首已下载但不想入库的歌曲时的完整语义:
1. 物理删除本地缓存文件 (与 SongManagementService.delete_song 相同)
2. 删除 Song 记录及其关联源
3. 将该歌的所有 (source, source_id) 写入 ignored_songs 墓碑表

为什么需要忽略表:
- 新歌监控 (NewReleaseMonitorService) 以 Song 表的 (source, source_id)
  差集判断"新歌"。若忽略只删 Song 而不留痕，下一轮监控会重新发现
  同一首歌并再次推送/下载 (死循环)。
- 自动下载队列消费时同样需要排除已忽略的键，避免忽略后仍落盘。

Author: music-monitor development team
Created: 2026-08-14
"""
import os
import logging
from typing import List, Optional, Set, Tuple

import anyio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ignored_song import IgnoredSong
from app.repositories.song import SongRepository
from app.utils.error_handler import handle_service_errors

logger = logging.getLogger(__name__)


class IgnoreService:
    """忽略歌曲服务"""

    # ==================== 忽略 ====================

    @handle_service_errors(fallback_value=False)
    async def ignore_song(self, db: AsyncSession, song_id: int) -> bool:
        """
        忽略一首歌曲: 删文件 + 删 Song + 写忽略墓碑。

        Args:
            db: 异步数据库会话。
            song_id: 待忽略歌曲 ID。

        Returns:
            bool: 成功返回 True，歌曲不存在或失败返回 False。
        """
        song_repo = SongRepository(db)
        song = await song_repo.get(song_id)

        if not song:
            return False

        # 1. 收集 (source, source_id) 键与标题快照 (删除前)
        keys: List[Tuple[str, str]] = []
        for src in song.sources:
            if src.source and src.source_id:
                keys.append((src.source, str(src.source_id)))
        title_snapshot = song.title or ''

        # 2. 删除本地文件
        if song.local_path:
            exists = await anyio.to_thread.run_sync(os.path.exists, song.local_path)
            if exists:
                try:
                    await anyio.to_thread.run_sync(os.remove, song.local_path)
                except OSError as e:
                    logger.warning(f"忽略时删除文件失败 (继续): {song.local_path}: {e}")

        # 3. 写忽略墓碑 (幂等 upsert: 已存在的键不重复插入)
        for source, source_id in keys:
            existing = (
                await db.execute(
                    select(IgnoredSong).where(
                        IgnoredSong.source == source,
                        IgnoredSong.source_id == source_id,
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    IgnoredSong(
                        artist_id=song.artist_id,
                        source=source,
                        source_id=source_id,
                        title=title_snapshot,
                    )
                )
                logger.info(f"[Ignore] 登记忽略: {source}:{source_id} ({title_snapshot})")
        if keys:
            await db.flush()

        # 4. 删除 Song 记录 (ORM 级联删除关联源)
        success = await song_repo.delete(song_id)
        return success

    # ==================== 查询 ====================

    @handle_service_errors(fallback_value=set())
    async def get_ignored_keys(
        self,
        db: AsyncSession,
        artist_id: Optional[int] = None,
    ) -> Set[Tuple[str, str]]:
        """
        查询被忽略的 (source, source_id) 键集合。

        Args:
            db: 异步数据库会话。
            artist_id: 可选，仅返回指定歌手的忽略键 (监控按歌手查询更高效)。

        Returns:
            Set[(source, source_id)]。
        """
        stmt = select(IgnoredSong.source, IgnoredSong.source_id)
        if artist_id is not None:
            stmt = stmt.where(IgnoredSong.artist_id == artist_id)
        result = await db.execute(stmt)
        return {(source, str(source_id)) for source, source_id in result.all()}

    @handle_service_errors(fallback_value=False)
    async def is_ignored(
        self,
        db: AsyncSession,
        source: str,
        source_id: str,
    ) -> bool:
        """
        判断某个 (source, source_id) 是否已被忽略。
        用于自动下载队列消费前的拦截。
        """
        stmt = select(IgnoredSong.id).where(
            IgnoredSong.source == source,
            IgnoredSong.source_id == str(source_id),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None


# 模块级单例 (与其它 Service 的 get_* 模式保持一致)
_service = None


def get_ignore_service() -> IgnoreService:
    """获取 IgnoreService 单例。"""
    global _service  # noqa: PLW0603 - 单例惰性初始化惯用法
    if _service is None:
        _service = IgnoreService()
    return _service
