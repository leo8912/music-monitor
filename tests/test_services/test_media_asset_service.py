# -*- coding: utf-8 -*-
"""
MediaAssetService 单元测试

覆盖 ensure_cover / ensure_avatar / ensure_localized 的分支：
1. 已本地化 (/uploads/) → 校验文件存在
2. 远程 URL → 下载并回写 /uploads/ 路径
3. 空值头像 → 先 ArtistSource.avatar 再搜索 fallback
4. 候选 URL 优先生效
"""
import os

import pytest

from app.models.artist import Artist, ArtistSource
from app.models.song import Song
from app.services.media_asset_service import MediaAssetService


class FakeAggregator:
    def __init__(self, candidates=None):
        self._candidates = candidates or []

    async def search_artist(self, keyword, limit=10):
        return self._candidates


class FakeCandidate:
    def __init__(self, name, avatar):
        self.name = name
        self.avatar = avatar
        self.source = "netease"
        self.id = "1"


@pytest.fixture
def svc(tmp_path, monkeypatch):
    s = MediaAssetService()
    # 指向临时目录，避免污染真实 uploads/
    s.upload_root = str(tmp_path / "uploads")
    s.cover_dir = os.path.join(s.upload_root, "covers")
    s.avatar_dir = os.path.join(s.upload_root, "avatars")
    os.makedirs(s.cover_dir, exist_ok=True)
    os.makedirs(s.avatar_dir, exist_ok=True)
    return s


# ---------------------------------------------------------------------------
# ensure_cover
# ---------------------------------------------------------------------------

async def test_ensure_cover_local_path_exists(svc, tmp_path):
    """已本地化的封面：文件存在 → True 且不改写。"""
    song = Song(title="t")
    fake_path = os.path.join(svc.cover_dir, "x.jpg")
    open(fake_path, "w").close()
    song.cover = "/uploads/covers/x.jpg"

    assert await svc.ensure_cover(song) is True
    assert song.cover == "/uploads/covers/x.jpg"


async def test_ensure_cover_local_path_missing(svc):
    """已本地化但文件缺失 → False。"""
    song = Song(title="t")
    song.cover = "/uploads/covers/ghost.jpg"

    assert await svc.ensure_cover(song) is False


async def test_ensure_cover_remote_downloads(svc, monkeypatch):
    """远程 URL → 下载并回写本地路径。"""
    async def fake_download(url, folder):
        assert url == "http://example.com/c.jpg"
        assert folder == "covers"
        return "/uploads/covers/abc.jpg", "/some/abc.jpg"
    monkeypatch.setattr(svc, "_download", fake_download)

    song = Song(title="t")
    song.cover = "http://example.com/c.jpg"

    assert await svc.ensure_cover(song) is True
    assert song.cover == "/uploads/covers/abc.jpg"


async def test_ensure_cover_empty_false(svc):
    """空 cover → False，不触发搜索。"""
    song = Song(title="t")
    song.cover = ""
    assert await svc.ensure_cover(song) is False


async def test_ensure_cover_candidate_url_wins(svc, monkeypatch):
    """candidate_url 优先生效。"""
    async def fake_download(url, folder):
        return "/uploads/covers/xyz.jpg", "/some/xyz.jpg"
    monkeypatch.setattr(svc, "_download", fake_download)

    song = Song(title="t", cover="http://old.jpg")
    assert await svc.ensure_cover(song, candidate_url="http://new.jpg") is True
    assert song.cover == "/uploads/covers/xyz.jpg"


# ---------------------------------------------------------------------------
# ensure_avatar
# ---------------------------------------------------------------------------

async def test_ensure_avatar_already_local(svc, tmp_path):
    """已本地化头像：校验文件存在。"""
    fake_path = os.path.join(svc.avatar_dir, "a.jpg")
    open(fake_path, "w").close()

    artist = Artist(name="张三")
    artist.avatar = "/uploads/avatars/a.jpg"

    assert await svc.ensure_avatar(artist) is True


async def test_ensure_avatar_candidate_downloads(svc, monkeypatch):
    """候选 URL → 下载到 avatars 并同步到 sources。"""
    async def fake_download(url, folder):
        assert folder == "avatars"
        return "/uploads/avatars/av.jpg", "/some/av.jpg"
    monkeypatch.setattr(svc, "_download", fake_download)

    artist = Artist(name="张三")
    src = ArtistSource(source="netease", source_id="1", avatar="")
    artist.sources.append(src)

    assert await svc.ensure_avatar(artist, candidate_url="http://x/av.jpg") is True
    assert artist.avatar == "/uploads/avatars/av.jpg"
    assert src.avatar == "/uploads/avatars/av.jpg"


async def test_ensure_avatar_uses_source_avatar_first(svc, monkeypatch):
    """空 avatar：先查 ArtistSource.avatar（http 开头）。"""
    async def fake_download(url, folder):
        return "/uploads/avatars/from_src.jpg", "/some/from_src.jpg"
    monkeypatch.setattr(svc, "_download", fake_download)

    artist = Artist(name="张三")
    artist.sources.append(
        ArtistSource(source="qqmusic", source_id="1", avatar="http://src/av.jpg")
    )

    assert await svc.ensure_avatar(artist) is True
    assert artist.avatar == "/uploads/avatars/from_src.jpg"


async def test_ensure_avatar_search_fallback(svc, monkeypatch):
    """空 avatar + 无 source 头像 → 搜索 fallback。"""
    async def fake_download(url, folder):
        return "/uploads/avatars/searched.jpg", "/some/searched.jpg"
    monkeypatch.setattr(svc, "_download", fake_download)
    svc._aggregator = FakeAggregator([FakeCandidate("张三", "http://found/av.jpg")])

    artist = Artist(name="张三")
    assert await svc.ensure_avatar(artist) is True
    assert artist.avatar == "/uploads/avatars/searched.jpg"


async def test_ensure_avatar_no_source_returns_false(svc, monkeypatch):
    """无 source 头像且搜索无结果 → False。"""
    svc._aggregator = FakeAggregator([])
    artist = Artist(name="未知歌手")
    assert await svc.ensure_avatar(artist) is False
    assert artist.avatar is None


# ---------------------------------------------------------------------------
# ensure_localized 分发
# ---------------------------------------------------------------------------

async def test_ensure_localized_dispatches(svc, monkeypatch):
    """按实体类型分发。"""
    async def fake_download(url, folder):
        return "/uploads/covers/dispatch.jpg", "/some/dispatch.jpg"
    monkeypatch.setattr(svc, "_download", fake_download)

    song = Song(title="t", cover="http://c.jpg")
    assert await svc.ensure_localized(song) is True
    assert song.cover.startswith("/uploads/")

    artist = Artist(name="李四", avatar="http://a.jpg")
    assert await svc.ensure_localized(artist) is True
    assert artist.avatar.startswith("/uploads/")
