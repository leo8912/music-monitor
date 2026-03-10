# -*- coding: utf-8 -*-
"""
全局单例服务管理

以下服务必须使用单例模式，不可在方法内 new 新实例：
- DownloadService: 内含 RateLimiter，多实例会导致频率限制失效
- MetadataService: 内含 Provider 缓存
- MusicAggregator: 内含连接池

使用方式:
    from app.services._singletons import get_download_service, get_aggregator, get_metadata_service
"""
import logging

logger = logging.getLogger(__name__)

_download_service = None
_metadata_service = None
_aggregator = None


def get_download_service():
    """获取 DownloadService 全局单例"""
    global _download_service
    if _download_service is None:
        from app.services.download_service import DownloadService
        _download_service = DownloadService()
        logger.debug("DownloadService 单例已创建")
    return _download_service


def get_metadata_service():
    """获取 MetadataService 全局单例"""
    global _metadata_service
    if _metadata_service is None:
        from app.services.metadata_service import MetadataService
        _metadata_service = MetadataService()
        logger.debug("MetadataService 单例已创建")
    return _metadata_service


def get_aggregator():
    """获取 MusicAggregator 全局单例"""
    global _aggregator
    if _aggregator is None:
        from app.services.music_providers.aggregator import MusicAggregator
        _aggregator = MusicAggregator()
        logger.debug("MusicAggregator 单例已创建")
    return _aggregator
