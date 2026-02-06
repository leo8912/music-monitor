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
from app.services.scan_service import ScanService
from app.services.metadata_healer import MetadataHealer
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
        self.metadata_healer = MetadataHealer()
        
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
        count = await self.artist_refresh_service.refresh(db, artist_name)
        
        # [Fix] Trigger pending downloads immediately
        try:
            logger.info("Triggering pending download queue after refresh...")
            await self.song_service.process_pending_queue(db)
        except Exception as e:
            logger.error(f"Failed to process pending queue: {e}")
            
        return count
    
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
        # 统一委托给 MetadataHealer
        # 修正：MetadataHealer 目前通过搜索匹配最佳元数据并写入标签
        # 虽然 MetadataHealer 目前主要依赖搜集匹配，但我们可以支持它。
        # 此处为了保持兼容性，直接调用 healer.heal_song
        # 此处为了保持兼容性，直接调用 healer.heal_song
        return await self.metadata_healer.heal_song(song_id, force=True)

    # ==================== 扫描服务 ====================
    
    async def scan_single_file(self, file_path: str, db: AsyncSession) -> Optional[any]:
        """
        扫描单个文件 (即时入库)
        
        委托给 ScanService
        """
        return await self.scan_service.scan_single_file(file_path, db)
