# -*- coding: utf-8 -*-
"""
NewReleaseMonitorService - 新歌增量监控服务

职责 (与全量 ArtistRefreshService 互补):
- 短周期、轻量地拉取每个活跃歌手的近期歌曲 (每源前 ~200 首)。
- 与库内 (source, source_id) 做差集，只增量落库，不跑全库元数据治愈/挽救。
- 发现新歌: 发「新歌发布」通知 -> 入自动下载队列 (下载成功后另发「试听通知」)。
- 用 Song.last_notified_at 抑制重复推送。

Author: music-monitor development team
"""
import logging
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.artist import Artist
from app.models.song import Song, SongSource
from app.services._singletons import get_aggregator
from app.services.scan_service import ScanService

logger = logging.getLogger(__name__)

# 轻量检查时每源拉取的数量 (按热度/时间排序，足够捕获近期新歌)
_RECENT_LIMIT = 200


class NewReleaseMonitorService:
    def __init__(self):
        self.aggregator = get_aggregator()

    async def check_artist(self, db: AsyncSession, artist: Artist) -> int:
        """检查单名歌手的新歌，返回新增数量。"""
        # 防御性: 重新加载歌手及其平台关联，避免依赖调用方预加载 sources
        stmt = (
            select(Artist)
            .options(selectinload(Artist.sources))
            .where(Artist.id == artist.id)
        )
        artist = (await db.execute(stmt)).scalar_one_or_none()
        if artist is None:
            return 0
        if not artist.sources:
            logger.info(f"[NewRelease] 歌手 {artist.name} 无平台关联，跳过")
            return 0

        # 1. 预加载现有歌曲及其源
        stmt = (
            select(Song)
            .options(selectinload(Song.sources))
            .where(Song.artist_id == artist.id)
        )
        existing_songs = (await db.execute(stmt)).scalars().all()

        norm_title_map = {
            ScanService._normalize_cn_brackets(s.title).lower().strip(): s
            for s in existing_songs
        }
        known_srcs = {
            (ss.source, str(ss.source_id))
            for s in existing_songs
            for ss in s.sources
        }

        new_count = 0
        for src in artist.sources:
            if src.source not in ("qqmusic", "netease"):
                continue
            provider = self.aggregator.get_provider(src.source)
            if not provider:
                continue

            try:
                raw = await provider.get_artist_songs(src.source_id, limit=_RECENT_LIMIT)
            except Exception as e:
                logger.warning(f"[NewRelease] {artist.name} 拉取 {src.source} 失败: {e}")
                continue

            candidates = [s for s in raw if self.aggregator._is_valid_song(s)]
            logger.info(
                f"[NewRelease] {artist.name} @ {src.source}: 取回 {len(raw)} 首，有效 {len(candidates)} 首"
            )

            for cand in candidates:
                key = (cand.source, str(cand.id))
                if key in known_srcs:
                    continue

                norm = ScanService._normalize_cn_brackets(cand.title).lower().strip()
                song = norm_title_map.get(norm)

                is_new_song = False
                if song is None:
                    song = Song(
                        artist_id=artist.id,
                        title=cand.title,
                        album=cand.album,
                        created_at=datetime.now(),
                        status="PENDING",
                        unique_key=str(uuid.uuid4()),
                        sources=[],
                    )
                    db.add(song)
                    await db.flush()
                    norm_title_map[norm] = song
                    is_new_song = True

                song_src_keys = {(ss.source, str(ss.source_id)) for ss in song.sources}
                if key not in song_src_keys:
                    song.sources.append(
                        SongSource(
                            song_id=song.id,
                            source=cand.source,
                            source_id=str(cand.id),
                            cover=cand.cover_url or getattr(cand, "pic_url", None),
                            duration=cand.duration,
                            url=getattr(cand, "url", None),
                            data_json={"quality": getattr(cand, "quality", "unknown")},
                        )
                    )

                if is_new_song:
                    await self._handle_new_song(db, song, cand)
                    new_count += 1

        if new_count > 0:
            await db.commit()
            logger.info(f"[NewRelease] {artist.name}: 新增 {new_count} 首")
        return new_count

    async def check_all(self, db: AsyncSession) -> dict:
        """遍历所有监控中的歌手做增量检查。"""
        stmt = select(Artist).options(selectinload(Artist.sources)).where(
            Artist.is_monitored == True
        )
        artists = (await db.execute(stmt)).scalars().all()

        if not artists:
            logger.info("[NewRelease] 没有监控中的歌手")
            return {"checked": 0, "new_songs": 0}

        total_new = 0
        for artist in artists:
            try:
                total_new += await self.check_artist(db, artist)
            except Exception as e:
                logger.error(f"[NewRelease] 检查 {artist.name} 失败: {e}", exc_info=True)

        logger.info(f"[NewRelease] 检查完成: {len(artists)} 位歌手，新增 {total_new} 首")
        return {"checked": len(artists), "new_songs": total_new}

    async def _handle_new_song(self, db: AsyncSession, song: Song, cand):
        """对新歌: 补全发布时间 -> 发发现通知 -> 入下载队列 -> 记录通知时间。"""
        from app.services.metadata_healer import MetadataHealer

        # 解析发布时间
        p_raw = getattr(cand, "publish_time", None)
        if p_raw and not song.publish_time:
            parsed = MetadataHealer()._parse_date(str(p_raw))
            if parsed:
                song.publish_time = parsed

        # 补全封面
        if not song.cover:
            song.cover = cand.cover_url or getattr(cand, "pic_url", None)

        snapshot = {
            "title": song.title,
            "artist": getattr(cand, "artist", ""),
            "album": song.album,
            "cover_url": song.cover,
            "publish_time": song.publish_time,
            "source": cand.source,
            "source_id": str(cand.id),
        }

        from app.services.notification import NotificationService

        try:
            await NotificationService.notify_new_song(snapshot)
            logger.info(f"🆕 [NewRelease] 发现新歌并已通知: {song.title}")
        except Exception as e:
            logger.error(f"[NewRelease] 新歌通知失败 ({song.title}): {e}", exc_info=True)

        try:
            from app.services.auto_download_service import get_auto_download_service

            await get_auto_download_service().add_to_queue([snapshot])
        except Exception as e:
            logger.error(f"[NewRelease] 自动下载入队失败 ({song.title}): {e}", exc_info=True)

        song.last_notified_at = datetime.now()

_service = None


def get_new_release_monitor() -> NewReleaseMonitorService:
    global _service
    if _service is None:
        _service = NewReleaseMonitorService()
    return _service
