"""
关注歌手服务 (Subscription Service)

核心功能:
1. 歌手关注/取消关注
2. 获取关注歌手列表
3. 智能关联多平台 ID (后台任务)

Author: google (Recovered)
Created: 2026-01-28
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.models.artist import Artist, ArtistSource
from app.models.song import Song
from app.services.music_providers.aggregator import MusicAggregator

# Global lock for artist addition to prevent duplicate creation on concurrent requests
_add_artist_lock = asyncio.Lock()

class SubscriptionService:
    @staticmethod
    async def get_monitored_artists(db: AsyncSession) -> List[Dict]:
        """
        获取所有关注的歌手。
        """
        from sqlalchemy import func
        stmt = select(Artist).options(selectinload(Artist.sources)).where(Artist.is_monitored == True).order_by(Artist.id.asc())
        result = await db.execute(stmt)
        artists = result.scalars().all()
        
        res = []
        for a in artists:
            # Get real song count from DB
            count_stmt = select(func.count()).select_from(Song).where(Song.artist_id == a.id)
            song_count = (await db.execute(count_stmt)).scalar() or 0
            
            source_list = [s.source for s in a.sources] if a.sources else []
            res.append({
                "name": a.name,
                "id": str(a.id),
                "source": "database",
                "sources": source_list,
                "avatar": a.avatar,
                "songCount": song_count
            })
        return res

    @staticmethod
    async def add_artist(db: AsyncSession, name: str, source: str, artist_id: str, avatar: str = "") -> bool:
        """
        [Instant Add] 极速添加歌手到本地数据库。
        使用 asyncio.Lock 确保并发安全。
        """
        async with _add_artist_lock:
            name = name.strip()
            artist_id = str(artist_id).strip()
            
            # 1. 检查该源是否已存在
            stmt = select(ArtistSource).where(
                ArtistSource.source == source, 
                ArtistSource.source_id == artist_id
            )
            result = await db.execute(stmt)
            existing_source = result.scalar_one_or_none()
            
            if existing_source:
                logger.info(f"Artist source already exists: {name} ({source}:{artist_id})")
                parent = await db.get(Artist, existing_source.artist_id)
                if parent and not parent.is_monitored:
                    parent.is_monitored = True
                    if avatar and not parent.avatar:
                        parent.avatar = avatar
                    db.add(parent)
                    await db.commit()
                return True

            # 2. 按名称查找逻辑艺人 (合并同名艺人)
            stmt = select(Artist).where(Artist.name == name)
            artist = (await db.execute(stmt)).scalars().first()
            
            if not artist:
                artist = Artist(name=name, avatar=avatar, is_monitored=True)
                db.add(artist)
                await db.flush() # 生成 ID
                logger.info(f"Created new logical artist: {name}")
            else:
                if avatar and not artist.avatar:
                    artist.avatar = avatar
                artist.is_monitored = True
                db.add(artist)
                logger.info(f"Merging source to existing artist: {name}")

            # 3. 创建源关联
            new_source = ArtistSource(
                artist_id=artist.id,
                source=source,
                source_id=artist_id,
                avatar=avatar or artist.avatar,
                url="" 
            )
            db.add(new_source)
            logger.info(f"Linked source {source}:{artist_id} to artist {artist.name}")
            
            await db.commit()
            return True

    @staticmethod
    async def smart_link_sources(db: AsyncSession, artist_name: str, known_source: str = None, known_id: str = None):
        """
        [Background Task] 后台搜寻并关联全平台 ID。
        """
        aggregator = MusicAggregator()
        logger.info(f"Smart Searching for artist: {artist_name} to find all IDs...")
        
        candidates = await aggregator.search_artist(artist_name, limit=10)
        
        stmt = select(Artist).where(Artist.name == artist_name)
        artist = (await db.execute(stmt)).scalars().first()
        
        if not artist:
            logger.error(f"Smart Link: Artist {artist_name} not found in DB")
            return

        # 更新头像
        if not artist.avatar:
            for cand in candidates:
                 if cand.avatar:
                     artist.avatar = cand.avatar
                     db.add(artist)
                     logger.info(f"Smart Link: Updated artist avatar from {cand.source}")
                     break

        potential_links = {}
        if known_source and known_id:
            potential_links[known_source] = str(known_id)

        target_clean = artist_name.lower().replace(' ', '')
        for cand in candidates:
            cand_clean = cand.name.lower().replace(' ', '')
            is_match = False
            
            # 模糊匹配逻辑
            if cand_clean == target_clean:
                is_match = True
            elif (cand_clean in target_clean or target_clean in cand_clean):
                 diff = abs(len(cand_clean) - len(target_clean))
                 if diff <= 5:
                     is_match = True
            
            if is_match:
                # 收集 ID
                potential_links[cand.source] = str(cand.id)
                if cand.extra_ids:
                    for k, v in cand.extra_ids.items():
                        potential_links[k] = str(v)
            
            logger.debug(f"Smart Link: Checking '{cand.name}' ({cand.source}) - Match: {is_match}")

        # 应用关联
        for s_src, s_id in potential_links.items():
            chk = select(ArtistSource).where(
                ArtistSource.artist_id == artist.id,
                ArtistSource.source == s_src
            )
            res = await db.execute(chk)
            if res.scalar_one_or_none():
                continue
                
            src_avatar = ""
            for cand in candidates:
                if cand.source == s_src and str(cand.id) == str(s_id):
                    src_avatar = cand.avatar
                    break

            new_source = ArtistSource(
                artist_id=artist.id,
                source=s_src,
                source_id=str(s_id),
                avatar=src_avatar or "",
                url="" 
            )
            db.add(new_source)
            logger.info(f"Smart Link: Linked {s_src}:{s_id} to {artist.name}")
            
        await db.commit()

    @staticmethod
    async def get_artist_detail(db: AsyncSession, artist_id: int) -> Optional[Dict]:
        """
        获取艺人详情，包含歌曲列表和专辑分组。
        
        返回格式:
        {
            "id": int,
            "name": str,
            "avatar": str,
            "sources": [str],
            "songs": [Song],
            "albums": [Album]
        }
        """
        from sqlalchemy.orm import selectinload
        from app.models.song import Song, SongSource
        
        stmt = select(Artist).options(
            selectinload(Artist.sources),
            selectinload(Artist.songs).selectinload(Song.sources)
        ).where(Artist.id == artist_id)
        
        result = await db.execute(stmt)
        artist = result.scalar_one_or_none()
        
        if not artist:
            return None
        
        # 构建歌曲列表
        songs = []
        albums = {}  # 用于去重专辑
        
        def get_publish_date(s):
            val = s.publish_time
            if not val:
                return datetime.min
            if isinstance(val, str):
                try:
                    # SQLite might return as string: '2024-01-01 00:00:00.000000'
                    return datetime.fromisoformat(val.split('.')[0])
                except:
                    return datetime.min
            return val

        for song in sorted(artist.songs, key=get_publish_date, reverse=True):
            # 确定主来源（优先本地）
            main_source = 'local' if song.local_path else None
            main_source_id = song.local_path if song.local_path else None
            
            if not main_source and song.sources:
                # 优先选择在线平台作为主来源
                platforms = [src for src in song.sources if src.source != 'local']
                if platforms:
                    main_source = platforms[0].source
                    main_source_id = platforms[0].source_id
                elif song.sources:
                    main_source = song.sources[0].source
                    main_source_id = song.sources[0].source_id
            
            # 收集所有可用来源
            available_sources = set()
            for src in song.sources:
                available_sources.add(src.source)
            
            # 如果是本地下载状态，添加标识
            if song.status == 'DOWNLOADED' or song.local_path:
                available_sources.add('downloaded')
            
            # 去重：如果同时有 local 和 downloaded，只保留 local
            if 'local' in available_sources and 'downloaded' in available_sources:
                available_sources.remove('downloaded')
            
            # 排序来源标签
            def source_sort_key(s):
                keys = {'local': 0, 'downloaded': 1, 'netease': 2, 'qqmusic': 3}
                return keys.get(s, 99)
            
            song_data = {
                "id": song.id,
                "title": song.title,
                "artist": artist.name,
                "album": song.album,
                "cover": song.cover,
                "publishTime": song.publish_time.isoformat() if song.publish_time else None,
                "isFavorite": song.is_favorite,
                "localPath": song.local_path,  # 添加本地路径
                "status": song.status or "PENDING",  # 添加状态
                "source": main_source or 'unknown',  # 主来源
                "sourceId": main_source_id or '',  # 主来源ID
                "availableSources": sorted(list(available_sources), key=source_sort_key)  # 所有可用来源
            }
            songs.append(song_data)
            
            # 收集专辑信息
            if song.album and song.album not in albums:
                albums[song.album] = {
                    "name": song.album,
                    "cover": song.cover,
                    "publishTime": song.publish_time.isoformat() if song.publish_time else None
                }
        
        return {
            "id": artist.id,
            "name": artist.name,
            "avatar": artist.avatar,
            "sources": [s.source for s in artist.sources],
            "songs": songs,
            "albums": list(albums.values())
        }

    @staticmethod
    async def delete_artist(db: AsyncSession, artist_id: int) -> int:
        """
        取消关注并删除歌手。
        """
        artist = await db.get(Artist, artist_id)
        if not artist:
            return 0
        await db.delete(artist)
        await db.commit()
        return 1
