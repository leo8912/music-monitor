# -*- coding: utf-8 -*-
"""
MediaService - 媒体服务业务逻辑处理

此文件提供媒体相关的业务逻辑处理，包括：
- 歌曲列表获取和搜索
- 音频文件下载和路径管理
- 歌曲收藏和状态管理

Author: google
Created: 2026-01-23
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from loguru import logger
import os
import logging
import uuid

from app.repositories.song import SongRepository
from app.repositories.artist import ArtistRepository
from app.models.song import Song
from app.models.download_history import DownloadHistory
from app.schemas import SongResponse
from core.config_manager import get_config_manager

# Setup logger
logger = logging.getLogger(__name__)


class MediaService:
    """媒体服务"""
    
    def __init__(self):
        pass

    async def get_songs(
        self,
        skip: int = 0,
        limit: int = 20,
        artist_id: Optional[int] = None,
        is_favorite: Optional[bool] = None,
        artist_name: Optional[str] = None,
        db: AsyncSession = None
    ) -> List[SongResponse]:
        """获取歌曲列表"""
        song_repo = SongRepository(db)
        
        filters = {}
        if artist_id is not None:
            filters['artist_id'] = artist_id
        if is_favorite is not None:
            filters['is_favorite'] = is_favorite
        if artist_name:
            from app.models.artist import Artist
            from sqlalchemy import select
            
            # Find Artist by name (exact)
            stmt = select(Artist.id).where(Artist.name == artist_name)
            result = await db.execute(stmt)
            found_id = result.scalar_one_or_none()
            if found_id:
                filters['artist_id'] = found_id
            else:
                return []
            
        songs = await song_repo.get_multi(skip=skip, limit=limit, filters=filters)
        
        result = []
        for song in songs:
            # Determine cover/album from local or sources?
            # Song model has prioritized cover/publish_time/title/album.
            # Local path is on Song.
            
            # Generate a unique key for frontend compatibility if needed
            # We can use the primary source key or just ID
            source_key = "unknown"
            if song.sources:
                primary = song.sources[0]
                source_key = f"{primary.source}_{primary.source_id}"
            
            result.append(SongResponse(
                id=song.id,
                title=song.title,
                artist=song.artist.name if song.artist else "Unknown",
                album=song.album or "",
                duration=0, # Deduce from sources if needed?
                cover_url=song.cover,
                lyric_url=None, # Need to fetch from linked source if needed
                local_audio_path=song.local_path,
                is_favorite=song.is_favorite,
                source=song.sources[0].source if song.sources else "local", # Approximate
                media_id=str(song.id), # Use ID as media_id for consistency
                unique_key=source_key,
                status=song.status,
                created_at=song.created_at.isoformat() if song.created_at else None,
                updated_at=song.created_at.isoformat() if song.created_at else None,
                publish_time=song.publish_time.isoformat() if song.publish_time else None
            ))
        
        return result

    async def get_audio_path(self, filename: str, db: AsyncSession = None) -> tuple[str, Optional[Song]]:
        """
        获取音频文件路径 (增强版: 支持跨平台路径修复)
        
        策略:
        1. 尝试直接从数据库查找 (local_path)
        2. 如果数据库路径不存在 (e.g. Windows路径在Docker中), 尝试在当前配置的目录中查找同名文件
        3. 尝试相对路径拼接
        """
        song_repo = SongRepository(db)
        
        # 1. 尝试从数据库查找
        # 即使这里查出的 song.local_path 是 D:/... 代码也会后续处理
        # 我们先尝试标准化 filename 查找
        normalized_filename = filename.replace("\\", "/")
        simple_filename = os.path.basename(normalized_filename) # song.mp3
        
        # 构造可能的数据库存储路径 (用于查询)
        possible_db_paths = [
            filename,
            normalized_filename,
            f"audio_cache/{simple_filename}",
            f"favorites/{simple_filename}",
            f"library/{simple_filename}"
        ]
        
        song = None
        for p in possible_db_paths:
            song = await song_repo.get_by_path(p)
            if song:
                break
        
        # 如果数据库还没找到，尝试模糊匹配 (危险? 暂不)
        
        final_path = None
        
        # A. 如果数据库有记录
        if song and song.local_path:
            # A1. 直接检查数据库记录的路径
            if os.path.exists(song.local_path):
                return song.local_path, song
            
            # A2. 路径不存在? 可能是环境迁移 (Win -> Docker)
            # 尝试在当前配置的目录中查找同名文件
            storage_cfg = get_config_manager().get("storage", {})
            dirs_to_check = [
                storage_cfg.get("cache_dir", "audio_cache"),
                storage_cfg.get("favorites_dir", "favorites"),
                storage_cfg.get("library_dir")
            ]
            
            # 提取文件名 (e.g. "Song.mp3")
            db_basename = os.path.basename(song.local_path)
            
            for d in dirs_to_check:
                if not d: continue
                candidate = os.path.join(d, db_basename)
                if os.path.exists(candidate):
                    logger.info(f"Using auto-healed path for {db_basename}: {candidate}")
                    return candidate, song

        # B. 如果数据库没记录，或者数据库记录也没救了
        # 尝试直接在文件系统查找 filename
        storage_cfg = get_config_manager().get("storage", {})
        dirs_to_check = [
            storage_cfg.get("cache_dir", "audio_cache"),
            storage_cfg.get("favorites_dir", "favorites"),
            storage_cfg.get("library_dir"),
            ".", # 当前目录
            "audio_cache", # 默认
            "favorites"
        ]
        
        target_name = os.path.basename(filename)
        
        for d in dirs_to_check:
            if not d: continue
            candidate = os.path.join(d, target_name)
            if os.path.exists(candidate):
                return candidate, song

        raise FileNotFoundError(f"Audio file not found: {filename}")

    async def download_audio(
        self,
        title: str,
        artist: str,
        album: str,
        source: str,
        source_id: str,
        cover_url: str = None,
        db: AsyncSession = None
    ):
        """下载音频文件"""
        from app.services.download_service import DownloadService
        from app.services.download_history_service import DownloadHistoryService
        from app.services.metadata_service import MetadataService
        from app.models.song import Song, SongSource
        from app.repositories.artist import ArtistRepository
        
        download_service = DownloadService()
        history_service = DownloadHistoryService()
        metadata_service = MetadataService()
        
        from core.websocket import manager
        
        # 记录下载开始
        await history_service.log_download_attempt(
            db, title, artist, album, source, source_id, 'PENDING', cover_url=cover_url
        )
        
        # 进度回调定义
        async def send_progress(msg: str):
            logger.info(f"Download Progress [{title}]: {msg}")
            # Identify song by unique_key (source_sourceid) if possible, or title/artist
            # Frontend uses currentSong in PlayerStore to match
            await manager.broadcast({
                "type": "download_progress",
                "title": title,
                "artist": artist,
                "source": source,
                "song_id": source_id,
                "message": msg,
                "timestamp": datetime.now().isoformat()
            })

        await send_progress("⏳ 正在启动下载任务...")
        
        try:
            # 1. Check Existing
            song_repo = SongRepository(db)
            existing_song = await song_repo.get_by_unique_key(source, source_id)
            
            if existing_song and existing_song.local_path and os.path.exists(existing_song.local_path):
                # Update status?
                if existing_song.status != "DOWNLOADED":
                     existing_song.status = "DOWNLOADED"
                     await db.commit()
                     
                await history_service.log_download_attempt(
                    db, title, artist, album, source, source_id, 
                    'SUCCESS', existing_song.local_path, cover_url=cover_url
                )
                return {
                    "message": "歌曲已存在",
                    "song_id": existing_song.id,
                    "already_exists": True,
                    "file_path": existing_song.local_path
                }
            
            # 2. Download
            result = await download_service.download_audio(
                title=title,
                artist=artist,
                album=album,
                progress_callback=send_progress
            )
            
            if result:
                # 3. Persist
                # Find/Create Artist
                artist_repo = ArtistRepository(db)
                # Note: This is an async method in updated Repo?
                artist_obj = await artist_repo.get_or_create_by_name(artist)
                
                # Fetch Meta
                metadata_result = await metadata_service.fetch_metadata(
                    title=title, artist=artist, source=source, source_id=source_id
                )
                
                # Create Song if not exists (existing_song might be None)
                if not existing_song:
                    existing_song = Song(
                        artist_id=artist_obj.id,
                        title=title,
                        album=metadata_result.album or album, 
                        local_path=result["local_path"],
                        status="DOWNLOADED",
                        created_at=datetime.now(),
                        cover=cover_url or metadata_result.cover_url,
                        unique_key=str(uuid.uuid4())
                    )
                    db.add(existing_song)
                    await db.flush() # ID
                else:
                    existing_song.local_path = result["local_path"]
                    existing_song.status = "DOWNLOADED"

                # Create SongSource (Download Source)
                source_entry = SongSource(
                    song_id=existing_song.id,
                    source=source,
                    source_id=source_id,
                    cover=cover_url,
                    data_json={
                        "lyrics": metadata_result.lyrics,
                        "quality": result.get("quality")
                    }
                )
                db.add(source_entry)
                
                # Create Local Source
                local_source = SongSource(
                    song_id=existing_song.id,
                    source="local",
                    source_id=os.path.basename(result["local_path"]),
                    url=result["local_path"]
                )
                db.add(local_source)
                
                await db.commit()
                
                # 4. 智能元数据补全 (非阻塞)
                try:
                    from app.services.enrichment_service import EnrichmentService
                    enrichment_service = EnrichmentService()
                    await enrichment_service.enrich_song(existing_song.id)
                    logger.info(f"✅ 自动补全元数据完成: {title}")
                except Exception as enrich_e:
                    logger.warning(f"⚠️ 元数据补全失败(非阻塞): {enrich_e}")
                
                await history_service.log_download_attempt(
                    db, title, artist, album, source, source_id, 
                    'SUCCESS', result["local_path"], cover_url=cover_url
                )
                
                return {
                    "message": "下载成功",
                    "song_id": existing_song.id,
                    "file_path": result["local_path"]
                }
            else:
                await history_service.log_download_attempt(
                    db, title, artist, album, source, source_id, 
                    'FAILED', error_message="下载失败", cover_url=cover_url
                )
                return {"message": "下载失败", "error": "Download failed"}
                
        except Exception as e:
            await history_service.log_download_attempt(
                db, title, artist, album, source, source_id, 
                'FAILED', error_message=str(e), cover_url=cover_url
            )
            # Log traceback for debugging
            import traceback
            traceback.print_exc()
            raise


# ========== 独立函数 ==========

async def find_artist_ids(artist_name: str) -> List[Dict[str, any]]:
    """搜索歌手ID"""
    from app.services.music_providers import MusicAggregator
    
    aggregator = MusicAggregator()
    results = await aggregator.search_artist(artist_name, limit=10)
    
    return [artist.to_dict() for artist in results]


async def check_file_integrity():
    """检查媒体文件完整性"""
    from core.database import AsyncSessionLocal
    from app.models.song import Song
    from sqlalchemy import select
    
    logger.info("开始文件完整性检查...")
    
    async with AsyncSessionLocal() as db:
        try:
            stmt = select(Song).where(Song.local_path.isnot(None))
            result = await db.execute(stmt)
            records = result.scalars().all()
            
            missing_count = 0
            for record in records:
                if record.local_path and not os.path.exists(record.local_path):
                    logger.warning(f"文件丢失: {record.title} at {record.local_path}")
                    record.status = "FILE_MISSING"
                    missing_count += 1
            
            if missing_count > 0:
                await db.commit()
            
            logger.info(f"文件完整性检查完成，丢失: {missing_count}")
            
        except Exception as e:
            logger.error(f"文件完整性检查错误: {e}")


async def auto_cache_recent_songs():
    """自动缓存最近的歌曲"""
    from core.database import AsyncSessionLocal
    from app.models.song import Song
    from sqlalchemy import select
    from datetime import timedelta
    
    logger.info("开始自动缓存...")
    
    async with AsyncSessionLocal() as db:
        try:
            yesterday = datetime.now() - timedelta(days=1)
            stmt = select(Song).where(
                Song.created_at > yesterday,
                Song.local_path.isnot(None)
            )
            result = await db.execute(stmt)
            recent_records = result.scalars().all()
            
            cached_count = 0
            for record in recent_records:
                if record.local_path and os.path.exists(record.local_path):
                    cached_count += 1
            
            logger.info(f"自动缓存完成，共 {cached_count} 首歌曲")
            
        except Exception as e:
            logger.error(f"自动缓存错误: {e}")