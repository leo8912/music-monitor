# -*- coding: utf-8 -*-
"""
P0 缺陷回归测试 (2026-08-14 代码审查发现)

覆盖三个已确认的真实缺陷, 防止修复后回归:

1. test_delete_artist_cascades_children / test_delete_song_cascades_sources
   [H1] 删除歌手/歌曲必须级联清理子表 (song_sources / artist_sources / songs)。
        BaseRepository.delete 已从 Core bulk delete 改为 ORM delete。
        修复前: 三张子表残留孤儿行 (已实测确认)。

2. test_rescue_orphan_songs_only_processes_local_songs
   [H2] _rescue_orphan_songs 必须只处理 local_path 非空的歌曲。
        修复前: `Song.local_path is not None` 恒为 True, 全部歌曲都进入挽救逻辑。

3. test_scan_endpoint_happy_path / test_library_service_exposes_scan_methods
   [H3] POST /api/system/scan 必须返回 200, LibraryService 必须暴露
        scan_local_files / enrich_metadata 门面方法。
        修复前: 调用不存在的 LibraryService 方法, 端点必定 500。
"""
from __future__ import annotations

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.artist import Artist, ArtistSource
from app.models.song import Song, SongSource
from app.services.artist_refresh_service import ArtistRefreshService
from app.services.library import LibraryService
from app.services.song_management_service import SongManagementService
from core.database import get_async_session


# ===========================================================================
# [H1] 级联删除
# ===========================================================================

async def _seed_artist_with_children(db: AsyncSession) -> Artist:
    """构造一个歌手 + 2 首歌 (各带 1 个平台源) + 1 个歌手平台源"""
    artist = Artist(name="测试歌手", is_monitored=True)
    db.add(artist)
    await db.flush()

    db.add(ArtistSource(
        artist_id=artist.id, source="qqmusic", source_id="mid_artist_1"
    ))

    for i in range(2):
        song = Song(
            unique_key=f"uk_test_{i}",
            title=f"测试歌曲{i}",
            artist_id=artist.id,
            status="DOWNLOADED",
            local_path=f"/tmp/nonexistent/song{i}.mp3",
        )
        db.add(song)
        await db.flush()
        db.add(SongSource(
            song_id=song.id, source="qqmusic", source_id=f"mid_song_{i}"
        ))

    await db.flush()
    return artist


async def test_delete_artist_cascades_children(db_session):
    """[H1] 删除歌手后: songs / song_sources / artist_sources 均无残留"""
    artist = await _seed_artist_with_children(db_session)
    await db_session.flush()

    service = SongManagementService()
    ok = await service.delete_artist(db_session, artist_id=artist.id)
    assert ok is True

    assert (await db_session.execute(select(Artist))).scalars().all() == []
    assert (await db_session.execute(select(Song))).scalars().all() == []
    assert (await db_session.execute(select(SongSource))).scalars().all() == []
    assert (await db_session.execute(select(ArtistSource))).scalars().all() == []


async def test_delete_song_cascades_sources(db_session):
    """[H1] 删除歌曲后: song_sources 无残留"""
    artist = await _seed_artist_with_children(db_session)
    song = (await db_session.execute(select(Song).where(Song.artist_id == artist.id))).scalars().first()
    assert song is not None

    service = SongManagementService()
    ok = await service.delete_song(db_session, song.id)
    assert ok is True

    remaining = (await db_session.execute(select(SongSource))).scalars().all()
    # 只剩另一首未删除歌曲的来源, 被删歌曲的来源已级联清除
    assert len(remaining) == 1
    assert remaining[0].song_id != song.id


# ===========================================================================
# [H2] 恒真条件: 只有本地歌曲进入挽救逻辑
# ===========================================================================

async def test_rescue_orphan_songs_only_processes_local_songs(db_session):
    """[H2] _rescue_orphan_songs 只处理 local_path 非空的歌曲

    修复前 `Song.local_path is not None` 恒为 True, 纯在线歌曲也会触发
    搜索挽救; 修复后 (`.isnot(None)`) 只对本地歌曲执行。
    """
    artist = Artist(name="挽救测试歌手", is_monitored=True)
    db_session.add(artist)
    await db_session.flush()

    # A: 有本地文件 (应被处理)
    song_local = Song(
        unique_key="uk_rescue_local",
        title="本地歌曲A",
        artist_id=artist.id,
        local_path="/tmp/nonexistent/rescue_a.mp3",
    )
    # B: 纯在线歌曲, 无 local_path (绝不应被处理)
    song_online = Song(
        unique_key="uk_rescue_online",
        title="在线歌曲B",
        artist_id=artist.id,
        local_path=None,
    )
    db_session.add_all([song_local, song_online])
    await db_session.flush()

    service = ArtistRefreshService()

    # mock 掉网络聚合器, 记录搜索关键词
    search_calls: list[str] = []

    async def fake_search(key: str, limit: int = 5):
        search_calls.append(key)
        return []

    service.aggregator.search_song = fake_search

    class FakeManager:
        async def broadcast(self, *args, **kwargs):
            pass

    await service._rescue_orphan_songs(
        db_session, artist, raw_songs=[], manager=FakeManager()
    )

    # B 的标题绝不应该出现在任何搜索关键词里
    assert not any(song_online.title in key for key in search_calls)
    # A 的标题应至少触发一次搜索
    assert any(song_local.title in key for key in search_calls)


# ===========================================================================
# [H3] 扫描端点
# ===========================================================================

async def test_library_service_exposes_scan_methods():
    """[H3] LibraryService 必须暴露 scan_local_files / enrich_metadata 门面方法"""
    service = LibraryService()
    assert callable(getattr(service, "scan_local_files"))
    assert callable(getattr(service, "enrich_metadata"))


@pytest_asyncio.fixture
async def scan_client(test_engine):
    """与 test_api_smoke 相同的最小 ASGI 客户端 (无 lifespan, DB 重定向, 鉴权关闭)"""
    from main import app

    factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def _override_session():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_async_session] = _override_session

    from core.config_manager import get_config_manager

    get_config_manager()._config.setdefault("auth", {})["enabled"] = False

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://scan") as client:
        yield client

    app.dependency_overrides.pop(get_async_session, None)


async def test_scan_endpoint_happy_path(scan_client, monkeypatch):
    """[H3] POST /api/system/scan 返回 200 且结构正确 (mock 掉真实扫描)"""
    async def fake_scan_local_files(db, *args, **kwargs):
        return 3

    async def fake_enrich_metadata(db, *args, **kwargs):
        return 2

    monkeypatch.setattr(LibraryService, "scan_local_files", fake_scan_local_files)
    monkeypatch.setattr(LibraryService, "enrich_metadata", fake_enrich_metadata)

    resp = await scan_client.post("/api/system/scan")
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["new_files_found"] == 3
    assert payload["metadata_enriched"] == 2
    assert payload["status"] == "success"


# ===========================================================================
# [H4] 失败路径 commit 不再抛 PendingRollbackError
# ===========================================================================

class _FakeSession:
    """模拟: 第一次 commit 抛异常 (事务失败), 回滚后第二次 commit 成功。"""

    def __init__(self, exc):
        self.exc = exc
        self.commits = 0
        self.rollbacks = 0

    def add(self, obj):
        pass

    async def commit(self):
        self.commits += 1
        if self.commits == 1:
            raise self.exc

    async def rollback(self):
        self.rollbacks += 1


async def test_safe_commit_recovers_after_failed_transaction():
    """[H4] _safe_commit 在事务失败后回滚清理并以独立事务重写, 不抛异常"""
    from sqlalchemy.exc import PendingRollbackError

    from app.services.download_history_service import DownloadHistoryService

    fake = _FakeSession(PendingRollbackError("xact already rolled back"))
    await DownloadHistoryService._safe_commit(fake, obj=object())
    assert fake.commits == 2  # 失败 1 次 + 重试 1 次
    assert fake.rollbacks == 1  # 失败后回滚清理


async def test_log_download_attempt_survives_failed_transaction(db_session):
    """
    [H4] 调用方事务已失败 (rollback-only) 时, log_download_attempt 必须
    正常落盘 FAILED 记录且不抛 PendingRollbackError。

    修复前: 内嵌 commit 抛 PendingRollbackError, 屏蔽 core.queue 的
    locked 重试逻辑 (异常信息不再包含 "database is locked")。
    """
    from sqlalchemy.exc import IntegrityError

    from app.models.download_history import DownloadHistory
    from app.services.download_history_service import DownloadHistoryService

    db = db_session

    # 制造失败事务: 重复 unique_key 触发 IntegrityError
    db.add(Song(unique_key="uk_h4_dup", title="a"))
    await db.flush()
    db.add(Song(unique_key="uk_h4_dup", title="b"))
    with pytest.raises(IntegrityError):
        await db.flush()
    # 此时事务已处于 rollback-only

    svc = DownloadHistoryService()
    record = await svc.log_download_attempt(
        db,
        title="H4测试",
        artist="歌手",
        album="专辑",
        source="netease",
        source_id="h4_001",
        status="FAILED",
    )
    assert record is not None

    # FAILED 记录应已落盘
    result = await db.execute(
        select(DownloadHistory).where(DownloadHistory.source_id == "h4_001")
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.download_status == "FAILED"
