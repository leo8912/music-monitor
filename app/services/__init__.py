# -*- coding: utf-8 -*-
"""
Service层 - 业务逻辑处理层

此目录包含所有业务逻辑处理服务，作为Router层和Repository层之间的桥梁。

主要服务:
- MediaService: 媒体播放/下载业务
- LibraryService: 本地媒体库管理  
- DownloadService: GDStudio API 下载
- MetadataService: 歌词/封面获取
- DownloadHistoryService: 下载历史记录
- HistoryService: 歌曲列表/去重
- WeChatDownloadService: 微信场景下载
- FavoritesService: 收藏管理

Author: google
Updated: 2026-01-26
"""
from .media_service import MediaService
from .library import LibraryService
from .download_service import DownloadService
from .download_history_service import DownloadHistoryService
from .metadata_service import MetadataService
from .history_service import HistoryService
from .wechat_download_service import WeChatDownloadService
from .favorites_service import FavoritesService
from .notification import NotificationService
from .subscription import SubscriptionService

__all__ = [
    "MediaService",
    "LibraryService", 
    "DownloadService",
    "DownloadHistoryService",
    "MetadataService",
    "HistoryService",
    "WeChatDownloadService",
    "FavoritesService",
    "NotificationService",
    "SubscriptionService",
]