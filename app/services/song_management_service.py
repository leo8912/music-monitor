# -*- coding: utf-8 -*-
"""
SongManagementService - 歌曲管理服务

功能：
- 删除歌曲
- 重新下载歌曲
- 从搜索结果下载歌曲
- 重置数据库

Author: google
Created: 2026-02-02 (从 LibraryService 拆分)
"""
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from datetime import datetime
import os
import re
import json
import logging
import anyio

from app.models.song import Song, SongSource
from app.models.artist import Artist, ArtistSource
from app.repositories.song import SongRepository
from app.repositories.artist import ArtistRepository
from app.services.download_service import DownloadService
from app.services.scraper import ScraperService
from app.services.metadata_service import MetadataService
from app.services.music_providers.aggregator import MusicAggregator
from app.services.scan_service import ScanService
from app.utils.error_handler import handle_service_errors

logger = logging.getLogger(__name__)


class SongManagementService:
    """歌曲增删改服务"""
    
    def __init__(self):
        self.aggregator = MusicAggregator()
        self.metadata_service = MetadataService()
    
    @handle_service_errors(fallback_value=False)
    async def delete_song(
        self, 
        db: AsyncSession, 
        song_id: int
    ) -> bool:
        """
        彻底删除一首歌曲。
        
        流程:
        1. 检查歌曲在数据库中是否存在。
        2. 如果存在本地音频文件，则从磁盘删除。
        3. 从数据库中移除歌曲及其所有关联的源 (Cascade Delete)。
        
        Args:
            db (AsyncSession): 异步数据库会话。
            song_id (int): 待删除的歌曲ID。
            
        Returns:
            bool: 删除成功返回 True，歌曲不存在或删除失败返回 False。
        """
        song_repo = SongRepository(db)
        song = await song_repo.get(song_id)
        
        if not song:
            return False
        
        # 删除本地文件
        if song.local_path:
            exists = await anyio.to_thread.run_sync(os.path.exists, song.local_path)
            if exists:
                await anyio.to_thread.run_sync(os.remove, song.local_path)
        
        # 从数据库删除
        success = await song_repo.delete(song_id)
        return success
    
    @handle_service_errors(fallback_value=False)
    async def delete_artist(
        self,
        db: AsyncSession,
        artist_id: int = None,
        artist_name: str = None
    ) -> bool:
        """
        删除歌手及其所有资源
        
        Args:
            db: 数据库会话
            artist_id: 歌手ID（可选）
            artist_name: 歌手名称（可选）
            
        Returns:
            是否删除成功
        """
        artist_repo = ArtistRepository(db)
        
        if artist_id:
            success = await artist_repo.delete(artist_id)
        elif artist_name:
            artist = await artist_repo.get_by_name(artist_name)
            if artist:
                success = await artist_repo.delete(artist.id)
            else:
                success = False
        else:
            success = False
        
        return success
    
    @handle_service_errors(fallback_value=False)
    async def redownload_song(
        self,
        db: AsyncSession,
        song_id: int,
        # ...
    ) -> bool:
        """
        重新下载指定的歌曲。
        
        该功能用于当本地文件损坏、品质不理想或丢失时，从指定源重新抓取：
        1. 调用 DownloadService 获取新的音频 URL。
        2. 下载并保存新的音频文件至 'audio_cache/'。
        3. 更新数据库中的 local_path 和状态。
        4. (可选) 删除旧的本地文件。
        5. 调用 ScraperService 重新抓取并嵌入元数据（封面、歌词等）。
        
        Args:
            db (AsyncSession): 异步数据库会话。
            song_id (int): 目标歌曲ID。
            source (str): 音乐平台标识 (netease/qqmusic)。
            source_id (str): 在该平台上的歌曲 ID。
            quality (int): 目标音质级别 (默认 999 最佳音质)。
            title (str, optional): 辅助定位的标题。
            artist (str, optional): 辅助定位的歌手名。
            
        Returns:
            bool: 重新下载并成功处理后返回 True。
        """
        logger.info(f"Redownload requested for song {song_id} from {source}:{source_id}")
        
        song_repo = SongRepository(db)
        song = await song_repo.get(song_id)
        if not song:
            logger.error(f"Song {song_id} not found")
            return False
        
        old_path = song.local_path
        
        # 1. 下载
        download_service = DownloadService()
        
        # 获取音频URL
        audio_info = await download_service.get_audio_url(source, source_id, quality)
        if not audio_info or not audio_info.get("url"):
            logger.error(f"Failed to get audio url for {source}:{source_id}")
            return False
        
        # 构造文件名
        target_title = audio_info.get("title") or title or song.title
        target_artist = audio_info.get("artist") or artist or (
            song.artist.name if song.artist else "Unknown"
        )
        
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', target_title)
        safe_artist = re.sub(r'[<>:"/\\|?*]', '_', target_artist)
        
        # 解析扩展名
        url = audio_info.get("url", "")
        ext = "mp3"
        if ".flac" in url.lower():
            ext = "flac"
        elif ".wav" in url.lower():
            ext = "wav"
        elif ".m4a" in url.lower():
            ext = "m4a"
        else:
            ext = "flac" if audio_info.get("br", 0) >= 740 else "mp3"
        
        filename = f"{safe_artist} - {safe_title}.{ext}"
        filepath = os.path.join(download_service.cache_dir, filename)
        
        # 下载文件
        success = await download_service.download_file(audio_info["url"], filepath)
        if not success:
            logger.error(f"Failed to download file to {filepath}")
            return False
        
        # 2. 更新数据库
        logger.info(f"Download successful: {filepath}")
        song.local_path = filepath
        song.status = "DOWNLOADED"
        await db.commit()
        
        # 3. 清理旧文件
        if old_path and old_path != filepath:
            if old_path and await anyio.to_thread.run_sync(os.path.exists, old_path):
                try:
                    await anyio.to_thread.run_sync(os.remove, old_path)
                    logger.info(f"Deleted old file: {old_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete old file: {e}")
        
        # 4. 刮削元数据
        try:
            scraper = ScraperService(
                aggregator=self.aggregator,
                metadata_service=self.metadata_service
            )
            await scraper.scrape_and_apply(db, song, source, source_id)
            logger.info("Metadata scraped and applied to new file.")
        except Exception as e:
            logger.error(f"Failed to apply metadata after redownload: {e}")
        
        return True
    
    @handle_service_errors(fallback_value={"success": False, "message": "Error occurred during download"})
    async def download_song_from_search(
        self,
        db: AsyncSession,
        title: str,
        artist: str,
        album: str,
        source: str,
        source_id: str,
        quality: int = 999,
        cover_url: str = None
    ) -> Dict:
        """
        直接从搜索结果中下载新歌曲并入库。
        
        流程:
        1. 检查目标歌曲是否已存在于库中（通过 source_id 或标题模糊匹配）。
        2. 如果需要，自动创建对应的歌手记录。
        3. 调用 DownloadService 执行文件下载。
        4. 将扫描到的或新建的 Song 记录关联新的本地文件，并更新 Source。
        5. 触发元数据刮削。
        
        Args:
            db (AsyncSession): 异步数据库会话。
            title (str): 歌曲名称。
            artist (str): 歌手名称。
            album (str): 专辑名称。
            source (str): 来源标识。
            source_id (str): 来源ID。
            quality (int): 音质等级。
            cover_url (str, optional): 封面图链接。
            
        Returns:
            Dict: 包含成功标志和处理后的歌曲数据对象 (去重后)。
        """
        logger.info(f"Direct download requested: {title} - {artist} [{source}:{source_id}]")
        
        # 1. 检查歌曲是否已存在（通过源ID匹配）
        stmt = select(SongSource).where(
            SongSource.source == source,
            SongSource.source_id == str(source_id)
        )
        existing_source = (await db.execute(stmt)).scalars().first()
        
        song = None
        if existing_source:
            song_repo = SongRepository(db)
            song = await song_repo.get(existing_source.song_id)
            if song:
                logger.info(f"Found existing song by source_id: {song.title} (ID: {song.id})")
        
        if not song:
            # 通过歌手+标题模糊匹配
            artist_repo = ArtistRepository(db)
            db_artist = await artist_repo.get_by_name(artist)
            
            if db_artist:
                norm_target = ScanService._normalize_cn_brackets(title).lower().strip()
                song_repo = SongRepository(db)
                artist_songs = await song_repo.get_by_artist(db_artist.id)
                
                for s in artist_songs:
                    norm_curr = ScanService._normalize_cn_brackets(s.title).lower().strip()
                    if norm_curr == norm_target:
                        song = s
                        logger.info(f"Found existing song by title match: {song.title}")
                        break
        
        # 2. 下载
        download_service = DownloadService()
        
        # 确保音质默认为高质量
        req_quality = quality if quality and quality > 0 else 999
        logger.info(f"Using quality: {req_quality} (requested: {quality})")
        
        audio_info = await download_service.get_audio_url(source, source_id, req_quality)
        if not audio_info or not audio_info.get("url"):
            logger.error(f"Failed to get audio url for {source}:{source_id}")
            return {"success": False, "message": "Failed to get audio URL"}
        
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
        safe_artist = re.sub(r'[<>:"/\\|?*]', '_', artist)
        
        # 扩展名
        url = audio_info.get("url", "")
        ext = "flac" if audio_info.get("br", 0) >= 740 else "mp3"
        if ".flac" in url.lower():
            ext = "flac"
        if ".wav" in url.lower():
            ext = "wav"
        if ".m4a" in url.lower():
            ext = "m4a"
        if ".mp3" in url.lower():
            ext = "mp3"
        
        filename = f"{safe_artist} - {safe_title}.{ext}"
        filepath = os.path.join(download_service.cache_dir, filename)
        
        # 执行下载
        dl_success = await download_service.download_file(audio_info["url"], filepath)
        if not dl_success:
            return {"success": False, "message": "Download failed"}
        
        # 3. 创建或更新数据库记录
        if not song:
            # 创建歌手（如果需要）
            artist_repo = ArtistRepository(db)
            db_artist = await artist_repo.get_by_name(artist)
            if not db_artist:
                db_artist = Artist(name=artist, avatar=cover_url)
                db.add(db_artist)
                await db.flush()
                
                # 创建歌手源
                if source and source_id:
                    new_as = ArtistSource(
                        artist_id=db_artist.id,
                        source=source,
                        source_id=str(source_id),
                        avatar=cover_url
                    )
                    db.add(new_as)
            else:
                # 更新头像（如果缺失）
                if not db_artist.avatar and cover_url:
                    db_artist.avatar = cover_url
            
            # 创建歌曲
            song = Song(
                title=title,
                artist_id=db_artist.id,
                album=album,
                cover=cover_url,
                publish_time=datetime.now(),  # 占位符
                created_at=datetime.now(),
                status="DOWNLOADED",
                local_path=filepath
            )
            db.add(song)
            await db.flush()
        else:
            # 更新现有歌曲
            if song.local_path and song.local_path != filepath and os.path.exists(song.local_path):
                try:
                    os.remove(song.local_path)
                except:
                    pass
            
            song.local_path = filepath
            song.status = "DOWNLOADED"
            
            # 更新缺失的元数据
            if not song.cover and cover_url:
                song.cover = cover_url
            if not song.album and album:
                song.album = album
        
        # 4. 添加/更新源
        chk = select(SongSource).where(
            SongSource.song_id == song.id,
            SongSource.source == source,
            SongSource.source_id == str(source_id)
        )
        src_ent = (await db.execute(chk)).scalars().first()
        
        if not src_ent:
            src_ent = SongSource(
                song_id=song.id,
                source=source,
                source_id=str(source_id),
                cover=cover_url,
                data_json=json.dumps({"quality": quality}, default=str)
            )
            db.add(src_ent)
        
        await db.commit()
        
        # 重新获取歌曲（带关系）
        stmt = select(Song).options(
            selectinload(Song.sources),
            selectinload(Song.artist)
        ).where(Song.id == song.id)
        song = (await db.execute(stmt)).scalars().first()
        
        # 5. 刮削元数据
        try:
            scraper = ScraperService(self.aggregator, self.metadata_service)
            await scraper.scrape_and_apply(db, song, source, source_id)
        except Exception as e:
            logger.warning(f"Metadata tagging failed: {e}")
        
        # 返回去重后的结果
        from app.services.deduplication_service import DeduplicationService
        items = DeduplicationService.deduplicate_songs([song])
        return {"success": True, "song": items[0] if items else None}
    
    @handle_service_errors(fallback_value=False)
    async def reset_database(self, db: AsyncSession) -> bool:
        """
        重置数据库（清空所有歌曲和歌手）
        
        Args:
            db: 数据库会话
            
        Returns:
            是否重置成功
        """
        try:
            # 删除所有歌曲
            await db.execute(delete(Song))
            
            # 删除所有歌手
            await db.execute(delete(Artist))
            
            await db.commit()
            logger.info("Database reset complete")
            return True
        except Exception as e:
            logger.error(f"Database reset failed: {e}")
            await db.rollback()
            return False
