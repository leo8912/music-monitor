# -*- coding: utf-8 -*-
"""
LibraryService - 本地媒体库管理服务 (Facade)

功能：
- 作为 Facade 模式的调度层
- 委托调用各个细粒度服务
- 保持对外 API 兼容性

注意:
- 具体业务逻辑已迁移至各专用服务
- 文件扫描功能在 ScanService
- 元数据补全功能在 EnrichmentService
- 歌手刷新功能在 ArtistRefreshService
- 收藏管理功能在 FavoriteService
- 歌曲管理功能在 SongManagementService

Author: google
Updated: 2026-02-02 (重构为 Facade 模式)
"""
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.services.artist_refresh_service import ArtistRefreshService
from app.services.favorite_service import FavoriteService
from app.services.song_management_service import SongManagementService
from app.services.scan_service import ScanService
from app.services.enrichment_service import EnrichmentService
from app.services.scraper import ScraperService
from app.services.metadata_service import MetadataService
from app.services.music_providers.aggregator import MusicAggregator

logger = logging.getLogger(__name__)


class LibraryService:
    """媒体库服务 (Facade)"""
    
    def __init__(self):
        # 注入各个专用服务
        self.artist_refresh_service = ArtistRefreshService()
        self.favorite_service = FavoriteService()
        self.song_service = SongManagementService()
        self.scan_service = ScanService()
        self.enrichment_service = EnrichmentService()
        
        # 保留聚合器用于兼容性
        self.aggregator = MusicAggregator()
    
    # ==================== 收藏管理 ====================
    
    async def toggle_favorite(
        self,
        song_id: int,
        db: AsyncSession = None
    ) -> Optional[Dict]:
        """
        切换歌曲收藏状态
        
        委托给 FavoriteService
        """
        return await self.favorite_service.toggle(db, song_id)
    
    # ==================== 歌曲管理 ====================
    
    async def delete_song(
        self,
        song_id: int,
        db: AsyncSession = None
    ) -> bool:
        """
        删除歌曲
        
        委托给 SongManagementService
        """
        return await self.song_service.delete_song(db, song_id)
    
    async def delete_artist(
        self,
        db: AsyncSession,
        artist_id: int = None,
        artist_name: str = None
    ) -> bool:
        """
        删除歌手及其资源
        
        委托给 SongManagementService
        """
        return await self.song_service.delete_artist(db, artist_id, artist_name)
    
    async def redownload_song(
        self,
        db: AsyncSession,
        song_id: int,
        source: str,
        source_id: str,
        quality: int = 999,
        title: str = None,
        artist: str = None
    ) -> bool:
        """
        重新下载歌曲
        
        委托给 SongManagementService
        """
        return await self.song_service.redownload_song(
            db, song_id, source, source_id, quality, title, artist
        )
    
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
        从搜索结果直接下载歌曲并入库
        
        委托给 SongManagementService
        """
        return await self.song_service.download_song_from_search(
            db, title, artist, album, source, source_id, quality, cover_url
        )
    
    async def reset_database(self, db: AsyncSession) -> bool:
        """
        重置数据库
        
        委托给 SongManagementService
        """
        return await self.song_service.reset_database(db)
    
    # ==================== 歌手刷新 ====================
    
    async def refresh_artist(self, db: AsyncSession, artist_name: str) -> int:
        """
        刷新歌手歌曲列表
        
        委托给 ArtistRefreshService
        """
        return await self.artist_refresh_service.refresh(db, artist_name)
    
    # ==================== 元数据匹配 ====================
    
    async def apply_metadata_match(
        self,
        db: AsyncSession,
        song_id: int,
        target_source: str,
        target_song_id: str
    ):
        """
        手动应用元数据匹配
        
        委托给 ScraperService
        """
        from app.repositories.song import SongRepository
        
        song_repo = SongRepository(db)
        song = await song_repo.get(song_id)
        
        if not song:
            logger.error(f"Song {song_id} not found")
            return False
        
        scraper = ScraperService(
            aggregator=self.aggregator,
            metadata_service=MetadataService()
        )
        
        await scraper.scrape_and_apply(db, song, target_source, target_song_id)
        return True
