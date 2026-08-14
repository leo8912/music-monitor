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
    """设置默认服务注册"""
    container = _container

    # 注册单例服务
    container.register_singleton("download_service", _create_download_service)
    container.register_singleton("metadata_service", _create_metadata_service)
    container.register_singleton("aggregator", _create_aggregator)
    container.register_singleton("media_asset_service", _create_media_asset_service)


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
