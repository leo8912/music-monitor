import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.artist import Artist, ArtistSource
from app.models.song import Song
from app.services.music_providers.base import SongInfo
from app.services import new_release_monitor as nr_mod
from app.services.notification import NotificationService


class FakeProvider:
    def __init__(self, songs):
        self._songs = songs

    async def get_artist_songs(self, artist_id, offset=0, limit=200):
        return list(self._songs)


class FakeAggregator:
    def __init__(self, songs_by_source):
        self._providers = {
            src: FakeProvider(songs) for src, songs in songs_by_source.items()
        }

    def get_provider(self, source_name):
        return self._providers.get(source_name)

    def _is_valid_song(self, song):
        return bool(song and song.title)


def make_song_info(title, source, song_id, artist="测试歌手",
                   album="专辑", cover="http://cover", pub="2026-01-01"):
    return SongInfo(
        title=title, artist=artist, album=album, source=source, id=song_id,
        cover_url=cover, duration=180, publish_time=pub,
    )


def build_service(songs_by_source, monkeypatch, notified, queued):
    monkeypatch.setattr(nr_mod, "get_aggregator", lambda: FakeAggregator(songs_by_source))

    async def _notify_stub(cls_or_self, snapshot):
        notified.append(snapshot)
    monkeypatch.setattr(NotificationService, "notify_new_song", classmethod(_notify_stub))

    from app.services import auto_download_service as ads

    class RecorderDownloader:
        async def add_to_queue(self, snapshots):
            queued.extend(snapshots)

    monkeypatch.setattr(ads, "get_auto_download_service", lambda: RecorderDownloader())

    # 避免构造真实 Aggregator (其会实例化真实 provider)
    return nr_mod.NewReleaseMonitorService()


def run_in_memory(coro_builder):
    """在每个测试自己的事件循环里跑，避免 pytest-asyncio 循环错位导致 MissingGreenlet。"""
    async def _main():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as db:
            await coro_builder(db)
        await engine.dispose()
    asyncio.run(_main())


def test_new_release_discover_and_notify(monkeypatch):
    async def scenario(db):
        artist = Artist(name="测试歌手", is_monitored=True)
        db.add(artist)
        await db.flush()
        db.add(ArtistSource(artist_id=artist.id, source="netease", source_id="n_1"))
        await db.flush()

        notified, queued = [], []
        service = build_service(
            {"netease": [make_song_info("新歌A", "netease", "n_100")]},
            monkeypatch, notified, queued,
        )
        new_count = await service.check_artist(db, artist)

        assert new_count == 1
        assert len(notified) == 1 and notified[0]["title"] == "新歌A"
        assert notified[0]["source_id"] == "n_100"
        assert queued and queued[0]["source_id"] == "n_100"

        songs = (await db.execute(select(Song))).scalars().all()
        assert len(songs) == 1
        assert songs[0].last_notified_at is not None
        assert len(songs[0].sources) == 1
        assert songs[0].sources[0].source_id == "n_100"

    run_in_memory(scenario)


def test_new_release_no_duplicate_on_recheck(monkeypatch):
    async def scenario(db):
        artist = Artist(name="测试歌手", is_monitored=True)
        db.add(artist)
        await db.flush()
        db.add(ArtistSource(artist_id=artist.id, source="netease", source_id="n_1"))
        await db.flush()

        notified, queued = [], []
        service = build_service(
            {"netease": [make_song_info("新歌A", "netease", "n_100")]},
            monkeypatch, notified, queued,
        )
        assert await service.check_artist(db, artist) == 1
        # 第二次运行：同一首已被收录，不回发通知、不入队新增
        assert await service.check_artist(db, artist) == 0
        assert len(notified) == 1
        assert len(queued) == 1

        songs = (await db.execute(select(Song))).scalars().all()
        assert len(songs) == 1

    run_in_memory(scenario)