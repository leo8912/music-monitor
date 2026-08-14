# -*- coding: utf-8 -*-
"""
CacheCleanupService 单元测试

验证核心安全边界:
- 孤儿文件 (DB 无记录) 会被清理
- **待定歌曲 (DB 有记录且文件在 cache 内) 不会被自动删除**
- 容量超限时按 mtime 从旧到新清理孤儿文件
- auto_cache_enabled=false 时跳过

Author: music-monitor QA
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from core.config_manager import get_config_manager
from core.storage import StoragePaths
from app.models.song import Song
from app.services.cache_cleanup_service import get_cache_cleanup_service


@pytest.fixture
def cache_env(tmp_path, monkeypatch):
    """配置 cache_dir 指向临时目录, 重置 StoragePaths 单例。"""
    cache_dir = tmp_path / "audio_cache"
    favorites_dir = tmp_path / "favorites"
    cache_dir.mkdir(parents=True, exist_ok=True)
    favorites_dir.mkdir(parents=True, exist_ok=True)

    cm = get_config_manager()
    cm._config["storage"] = {
        "cache_dir": str(cache_dir),
        "favorites_dir": str(favorites_dir),
        "library_dir": None,
        "auto_cache_enabled": True,
        "max_cache_size": 10 * 1024 * 1024,   # 10MB
        "cleanup_threshold": 0.8,             # 用到 8MB 触发
        "retention_days": 30,
    }
    StoragePaths.reset()

    yield cache_dir

    StoragePaths.reset()


def _touch(path: Path, size: int = 1024, mtime: float | None = None) -> Path:
    """写入指定大小的文件, 可选 mtime。"""
    path.write_bytes(b"x" * size)
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


async def test_cleanup_removes_orphan_but_keeps_pending(cache_env, db_session):
    """孤儿文件删除, 待定歌曲 (DB 有记录) 保留。"""
    cache_dir = cache_env

    # 孤儿文件 (DB 无记录)
    orphan = _touch(cache_dir / "orphan.mp3", size=2048, mtime=time.time() - 40 * 86400)

    # 待定歌曲 (DB 有记录, 文件在 cache 内)
    pending_file = _touch(cache_dir / "pending.mp3", size=1024, mtime=time.time() - 1 * 86400)
    song = Song(
        unique_key="test-pending-1",
        title="待定歌曲",
        status="DOWNLOADED",
        local_path=str(pending_file),
        is_favorite=False,
    )
    db_session.add(song)
    await db_session.commit()

    result = await get_cache_cleanup_service().cleanup(db_session)

    assert result["removed_count"] == 1
    assert result["kept_pending"] == 1
    assert not orphan.exists(), "孤儿文件应被删除"
    assert pending_file.exists(), "待定歌曲文件必须保留"


async def test_cleanup_respects_retention_days(cache_env, db_session):
    """未超保留期的孤儿文件不清理。"""
    cache_dir = cache_env

    fresh = _touch(cache_dir / "fresh_orphan.mp3", size=2048, mtime=time.time() - 1 * 86400)
    old = _touch(cache_dir / "old_orphan.mp3", size=2048, mtime=time.time() - 40 * 86400)

    result = await get_cache_cleanup_service().cleanup(db_session)

    assert result["removed_count"] == 1
    assert not old.exists()
    assert fresh.exists(), "未超保留期的孤儿不应删除"


async def test_cleanup_capacity_limit(cache_env, db_session, monkeypatch):
    """容量超限时按 mtime 从旧到新清理孤儿文件。"""
    cache_dir = cache_env

    # 设置很小上限: 1MB * 0.8 = 0.8MB 触发, 单个 1MB 文件清完仍超限
    cm = get_config_manager()
    cm._config["storage"]["max_cache_size"] = 1024 * 1024
    StoragePaths.reset()

    # 两个孤儿均未超保留期 (10 天内), 但总量 2MB 超阈值 0.8MB
    old = _touch(cache_dir / "old_1mb.mp3", size=1024 * 1024, mtime=time.time() - 10 * 86400)
    newer = _touch(cache_dir / "newer_1mb.mp3", size=1024 * 1024, mtime=time.time() - 5 * 86400)

    result = await get_cache_cleanup_service().cleanup(db_session)

    # 清掉最旧的 1MB 后剩余 1MB 仍 > 0.8MB, 继续清第二个
    assert result["removed_count"] == 2
    assert not old.exists() and not newer.exists(), "超过阈值后应继续清理孤儿"


async def test_cleanup_skipped_when_disabled(cache_env, db_session):
    """auto_cache_enabled=false 时跳过清理。"""
    cm = get_config_manager()
    cm._config["storage"]["auto_cache_enabled"] = False
    StoragePaths.reset()

    _touch(cache_env / "orphan.mp3", size=2048, mtime=time.time() - 40 * 86400)

    result = await get_cache_cleanup_service().cleanup(db_session)

    assert result.get("skipped") is True
    assert result["removed_count"] == 0
    assert (cache_env / "orphan.mp3").exists(), "禁用时不应删除任何文件"
