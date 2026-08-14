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
from app.services.metadata_healer import MetadataHealer
from app.container import get_aggregator

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
        self.song_repo = None
        self.artist_repo = None
        self.aggregator = get_aggregator()

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
        # 统一委托给 MetadataHealer，传入用户指定的数据源和歌曲 ID
        return await self.metadata_healer.heal_song(
            db, song_id, force=True,
            target_source=target_source,
            target_song_id=target_song_id
        )

    # ==================== 本地文件专属操作 ====================

    async def get_local_songs_paginated(
        self,
        db: AsyncSession,
        offset: int,
        fetch_limit: int,
        sort_by: str,
        order: str
    ) -> tuple[list, int]:
        """专门获取所有本地歌曲，委托给 SongManagementService"""
        return await self.song_service.get_local_songs_paginated(
            db, offset, fetch_limit, sort_by, order
        )

    async def force_fix_quality(self, db: AsyncSession) -> tuple[int, list]:
        """强制修复质量信息，委托给 SongManagementService"""
        return await self.song_service.force_fix_quality(db)

    # ==================== 扫描服务 ====================

    async def scan_local_files(self, db: AsyncSession) -> int:
        """
        全量扫描本地资料库并入库新文件

        委托给 ScanService; 返回本次新增入库的文件数。

        Args:
            db: 数据库会话 (透传给 ScanService)
        """
        result = await self.scan_service.scan_local_files(db)
        if isinstance(result, dict):
            return int(result.get("new_files_found", 0))
        return 0

    async def enrich_metadata(self, db: AsyncSession, limit: int = 5) -> int:
        """
        小批量元数据补全 (手动触发)

        委托给 MetadataHealer; 返回本次成功修复的歌曲数。
        注意: heal_all 内部自行管理会话 (AsyncSessionLocal),
        此处 db 仅用于保持 Facade 接口一致。

        Args:
            db: 数据库会话 (当前实现不使用, 保持签名兼容)
            limit: 单次批处理上限
        """
        return await self.metadata_healer.heal_all(force=False, limit=limit)

    async def scan_single_file(self, file_path: str, db: AsyncSession) -> Optional[any]:
        """
        扫描单个文件 (即时入库)

        委托给 ScanService
        """
        return await self.scan_service.scan_single_file(file_path, db)
