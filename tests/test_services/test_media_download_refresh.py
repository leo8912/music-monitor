# -*- coding: utf-8 -*-
"""
download_audio 下载完成后广播 refresh_songs 的回归测试。

用户场景: 点试听歌曲 → 下载完成 → 主界面应自动刷新显示本地歌曲。
根因: media_service.download_audio 落库后从不广播 refresh_songs,
      前端列表持有旧对象 (local_path=None) 直到手动刷新。
修复: 落库后广播 {"type": "refresh_songs", ...}, 前端 WebSocket 收到后刷新列表。
"""
import pytest
from unittest.mock import AsyncMock

from app.services.media_service import MediaService


@pytest.fixture
def svc():
    return MediaService()


async def test_download_audio_broadcasts_refresh_songs(
    db_session, monkeypatch, tmp_path, svc
):
    """下载成功落库后必须广播 refresh_songs，触发前端刷新列表。"""
    broadcasts = []

    async def fake_broadcast(msg):
        broadcasts.append(msg)

    monkeypatch.setattr("core.websocket.manager.broadcast", fake_broadcast)

    fake_file = tmp_path / "test_song.mp3"
    fake_file.write_bytes(b"fake audio")

    from app.models.artist import Artist
    artist = Artist(name="测试歌手")
    db_session.add(artist)
    await db_session.flush()

    from app.services import media_service as ms_mod

    # ---- 依赖打桩 ----
    # SongRepository.get_by_unique_key -> None (全新下载)
    monkeypatch.setattr(
        "app.repositories.song.SongRepository.get_by_unique_key",
        AsyncMock(return_value=None),
    )
    # ArtistRepository.get_or_create_by_name -> 已建 artist
    monkeypatch.setattr(
        "app.repositories.artist.ArtistRepository.get_or_create_by_name",
        AsyncMock(return_value=artist),
    )
    # _singletons.get_download_service
    async def fake_download_audio(title, artist, album, progress_callback=None):
        await progress_callback("✅ 下载完成！")
        return {"local_path": str(fake_file), "quality": "HQ"}

    monkeypatch.setattr(
        "app.services._singletons.get_download_service",
        lambda: type("D", (), {"download_audio": AsyncMock(side_effect=fake_download_audio)})(),
    )
    # _singletons.get_metadata_service
    class FakeMeta:
        album = "测试专辑"
        cover_url = "http://x/cover.jpg"
        lyrics = ""

    async def fake_fetch_metadata(title, artist, source, source_id):
        return FakeMeta()

    monkeypatch.setattr(
        "app.services._singletons.get_metadata_service",
        lambda: type("M", (), {"fetch_metadata": AsyncMock(side_effect=fake_fetch_metadata)})(),
    )
    # DownloadHistoryService.log_download_attempt
    monkeypatch.setattr(
        "app.services.download_history_service.DownloadHistoryService.log_download_attempt",
        AsyncMock(return_value=None),
    )
    # MetadataHealer.heal_song / LibraryService.scan_single_file /
    # MediaAssetService.ensure_cover 均为非阻塞局部 import，桩掉避免真实 IO
    monkeypatch.setattr(
        "app.services.metadata_healer.MetadataHealer.heal_song",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "app.services.library.LibraryService.scan_single_file",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "app.services.media_asset_service.MediaAssetService.ensure_cover",
        AsyncMock(return_value=True),
    )

    result = await svc.download_audio(
        title="测试歌曲", artist="测试歌手", album="测试专辑",
        source="netease", source_id="12345", db=db_session
    )

    assert result is not None
    refresh_msgs = [b for b in broadcasts if b.get("type") == "refresh_songs"]
    assert refresh_msgs, f"未广播 refresh_songs, 实际广播: {broadcasts}"
    assert refresh_msgs[0]["title"] == "测试歌曲"
