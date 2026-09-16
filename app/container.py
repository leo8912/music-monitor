"""
轻量级 DI 容器

管理应用程序的依赖生命周期，包括：
- 单例服务（DownloadService, MusicAggregator 等）
- 配置对象
- 数据库会话工厂
"""

from typing import Optional, Callable, TypeVar, Dict, Any
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Container:
    """轻量级依赖注入容器"""

    def __init__(self):
        # 单例实例缓存
        self._singletons: Dict[str, Any] = {}
        # 工厂函数注册
        self._factories: Dict[str, Callable] = {}

    def register_singleton(self, key: str, factory: Callable[[], T]) -> None:
        """注册单例工厂"""
        self._factories[key] = factory
        # 清除旧实例（如果存在）
        self._singletons.pop(key, None)

    def register_instance(self, key: str, instance: T) -> None:
        """直接注册实例"""
        self._singletons[key] = instance

    def resolve(self, key: str) -> T:
        """解析依赖（单例返回缓存，新建返回新实例）"""
        # 先检查缓存
        if key in self._singletons:
            return self._singletons[key]

        # 检查工厂
        if key in self._factories:
            instance = self._factories[key]()
            self._singletons[key] = instance
            logger.debug(f"Container: 创建单例 {key}")
            return instance

        raise KeyError(f"Container: 未注册的依赖 {key}")

    def has(self, key: str) -> bool:
        """检查依赖是否已注册"""
        return key in self._singletons or key in self._factories

    def clear(self) -> None:
        """清除所有单例实例（用于测试）"""
        self._singletons.clear()

    def reset(self, key: str) -> None:
        """重置单个单例（用于测试）"""
        self._singletons.pop(key, None)


# 全局容器实例
_container: Optional[Container] = None


def get_container() -> Container:
    """获取全局容器实例"""
    global _container  # noqa: PLW0603 - 单例容器惰性初始化惯用法
    if _container is None:
        _container = Container()
        _setup_default_services()
    return _container


def _setup_default_services() -> None:
    """设置默认服务注册

    所有有状态的服务（持有内部配置/缓存/连接池）均注册为单例，
    通过 Container 管理生命周期，避免路由层反复 new。
    """
    container = _container

    # --- 核心单例服务 ---
    container.register_singleton("download_service", _create_download_service)
    container.register_singleton("metadata_service", _create_metadata_service)
    container.register_singleton("aggregator", _create_aggregator)
    container.register_singleton("media_asset_service", _create_media_asset_service)

    # --- 业务服务 ---
    container.register_singleton("scan_service", _create_scan_service)
    container.register_singleton("library_service", _create_library_service)
    container.register_singleton("favorite_service", _create_favorite_service)
    container.register_singleton("song_management_service", _create_song_management_service)
    container.register_singleton("metadata_healer", _create_metadata_healer)
    container.register_singleton("deduplication_service", _create_deduplication_service)
    container.register_singleton("history_service", _create_history_service)
    container.register_singleton("download_history_service", _create_download_history_service)
    container.register_singleton("tag_service", _create_tag_service)
    container.register_singleton("ignore_service", _create_ignore_service)
    container.register_singleton("media_service", _create_media_service)

    # --- 监控/通知 ---
    container.register_singleton("task_monitor", _create_task_monitor)
    container.register_singleton("notification_service", _create_notification_service)
    container.register_singleton("auto_download_service", _create_auto_download_service)
    container.register_singleton("new_release_monitor", _create_new_release_monitor)
    container.register_singleton("cache_cleanup_service", _create_cache_cleanup_service)
    container.register_singleton("artist_refresh_service", _create_artist_refresh_service)

    # --- WeChat ---
    container.register_singleton("wechat_download_service", _create_wechat_download_service)
    container.register_singleton("wechat_session_service", _create_wechat_session_service)


def _create_download_service():
    """创建 DownloadService 单例"""
    from app.services.download_service import DownloadService
    logger.debug("创建 DownloadService 单例")
    return DownloadService()


def _create_metadata_service():
    """创建 MetadataService 单例"""
    from app.services.metadata_service import MetadataService
    logger.debug("创建 MetadataService 单例")
    return MetadataService()


def _create_aggregator():
    """创建 MusicAggregator 单例"""
    from app.services.music_providers.aggregator import MusicAggregator
    logger.debug("创建 MusicAggregator 单例")
    return MusicAggregator()


def _create_media_asset_service():
    """创建 MediaAssetService 单例"""
    from app.services.media_asset_service import MediaAssetService
    logger.debug("创建 MediaAssetService 单例")
    return MediaAssetService()


# --- 业务服务工厂 ---

def _create_scan_service():
    from app.services.scan_service import ScanService
    logger.debug("创建 ScanService 单例")
    return ScanService()


def _create_library_service():
    from app.services.library import LibraryService
    logger.debug("创建 LibraryService 单例")
    return LibraryService()


def _create_favorite_service():
    from app.services.favorite_service import FavoriteService
    logger.debug("创建 FavoriteService 单例")
    return FavoriteService()


def _create_song_management_service():
    from app.services.song_management_service import SongManagementService
    logger.debug("创建 SongManagementService 单例")
    return SongManagementService()


def _create_metadata_healer():
    from app.services.metadata_healer import MetadataHealer
    logger.debug("创建 MetadataHealer 单例")
    return MetadataHealer()


def _create_deduplication_service():
    from app.services.deduplication_service import DeduplicationService
    logger.debug("创建 DeduplicationService 单例")
    return DeduplicationService()


def _create_history_service():
    from app.services.history_service import HistoryService
    logger.debug("创建 HistoryService 单例")
    return HistoryService()


def _create_download_history_service():
    from app.services.download_history_service import DownloadHistoryService
    logger.debug("创建 DownloadHistoryService 单例")
    return DownloadHistoryService()


def _create_tag_service():
    from app.services.tag_service import TagService
    logger.debug("创建 TagService 单例")
    return TagService()


def _create_ignore_service():
    from app.services.ignore_service import IgnoreService
    logger.debug("创建 IgnoreService 单例")
    return IgnoreService()


def _create_media_service():
    from app.services.media_service import MediaService
    logger.debug("创建 MediaService 单例")
    return MediaService()


# --- 监控/通知工厂 ---

def _create_task_monitor():
    """注意: TaskMonitor 在模块级有 task_monitor 单例，此处保持兼容。"""
    from app.services.task_monitor import task_monitor
    logger.debug("使用模块级 TaskMonitor 单例")
    return task_monitor


def _create_notification_service():
    from app.services.notification import NotificationService
    logger.debug("创建 NotificationService 单例")
    return NotificationService()


def _create_auto_download_service():
    from app.services.auto_download_service import AutoDownloadService
    logger.debug("创建 AutoDownloadService 单例")
    return AutoDownloadService()


def _create_new_release_monitor():
    from app.services.new_release_monitor import NewReleaseMonitor
    logger.debug("创建 NewReleaseMonitor 单例")
    return NewReleaseMonitor()


def _create_cache_cleanup_service():
    from app.services.cache_cleanup_service import CacheCleanupService
    logger.debug("创建 CacheCleanupService 单例")
    return CacheCleanupService()


def _create_artist_refresh_service():
    from app.services.artist_refresh_service import ArtistRefreshService
    logger.debug("创建 ArtistRefreshService 单例")
    return ArtistRefreshService()


# --- WeChat 工厂 ---

def _create_wechat_download_service():
    from app.services.wechat_download_service import WechatDownloadService
    logger.debug("创建 WechatDownloadService 单例")
    return WechatDownloadService()


def _create_wechat_session_service():
    from app.services.wechat_session_service import WechatSessionService
    logger.debug("创建 WechatSessionService 单例")
    return WechatSessionService()


# 便利函数（与 _singletons.py 兼容）
def get_download_service():
    """获取 DownloadService 单例"""
    return get_container().resolve("download_service")


def get_metadata_service():
    """获取 MetadataService 单例"""
    return get_container().resolve("metadata_service")


def get_aggregator():
    """获取 MusicAggregator 单例"""
    return get_container().resolve("aggregator")


def get_media_asset_service():
    """获取 MediaAssetService 单例"""
    return get_container().resolve("media_asset_service")


def get_scan_service():
    return get_container().resolve("scan_service")


def get_library_service():
    return get_container().resolve("library_service")


def get_favorite_service():
    return get_container().resolve("favorite_service")


def get_song_management_service():
    return get_container().resolve("song_management_service")


def get_metadata_healer():
    return get_container().resolve("metadata_healer")


def get_deduplication_service():
    return get_container().resolve("deduplication_service")


def get_history_service():
    return get_container().resolve("history_service")


def get_download_history_service():
    return get_container().resolve("download_history_service")


def get_tag_service():
    return get_container().resolve("tag_service")


def get_ignore_service():
    return get_container().resolve("ignore_service")


def get_media_service():
    return get_container().resolve("media_service")


def get_task_monitor():
    return get_container().resolve("task_monitor")


def get_notification_service():
    return get_container().resolve("notification_service")


def get_auto_download_service():
    return get_container().resolve("auto_download_service")


def get_new_release_monitor():
    return get_container().resolve("new_release_monitor")


def get_cache_cleanup_service():
    return get_container().resolve("cache_cleanup_service")


def get_artist_refresh_service():
    return get_container().resolve("artist_refresh_service")


def get_wechat_download_service():
    return get_container().resolve("wechat_download_service")


def get_wechat_session_service():
    return get_container().resolve("wechat_session_service")
