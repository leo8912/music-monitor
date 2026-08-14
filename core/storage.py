"""
Storage Paths Management

统一管理应用中的所有存储路径：
- 音频缓存目录（cache_dir）
- 收藏夹目录（favorites_dir）
- 媒体库目录（library_dir）
- 上传目录（uploads）

提供：
- 路径解析和规范化
- 单一的配置入口
- DiskCache 容量管理
"""

import os
from pathlib import Path
from typing import Optional
from core.config_manager import get_config_manager


class StoragePaths:
    """存储路径管理器"""

    _instance: Optional["StoragePaths"] = None

    def __init__(self):
        self._config_manager = get_config_manager()
        self._storage_config = self._config_manager.get('storage', {})
        self._cache_dir: Optional[Path] = None
        self._favorites_dir: Optional[Path] = None
        self._library_dir: Optional[Path] = None
        self._uploads_dir: Optional[Path] = None

    @classmethod
    def get_instance(cls) -> "StoragePaths":
        """单例入口"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """用于测试的重置"""
        cls._instance = None

    @property
    def cache_dir(self) -> Path:
        """获取音频缓存目录"""
        if self._cache_dir is None:
            path_str = self._storage_config.get('cache_dir', 'audio_cache')
            self._cache_dir = Path(path_str).resolve()
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        return self._cache_dir

    @property
    def favorites_dir(self) -> Path:
        """获取收藏夹目录"""
        if self._favorites_dir is None:
            path_str = self._storage_config.get('favorites_dir', 'favorites')
            self._favorites_dir = Path(path_str).resolve()
            self._favorites_dir.mkdir(parents=True, exist_ok=True)
        return self._favorites_dir

    @property
    def library_dir(self) -> Optional[Path]:
        """获取媒体库目录（可选）"""
        if self._library_dir is None:
            path_str = self._storage_config.get('library_dir')
            if path_str:
                self._library_dir = Path(path_str).resolve()
                self._library_dir.mkdir(parents=True, exist_ok=True)
        return self._library_dir

    @property
    def uploads_dir(self) -> Path:
        """获取上传目录"""
        if self._uploads_dir is None:
            # 检查是否在容器环境中
            if os.path.exists('/config'):
                path_str = '/config/uploads'
            else:
                path_str = 'uploads'
            self._uploads_dir = Path(path_str).resolve()
            self._uploads_dir.mkdir(parents=True, exist_ok=True)
        return self._uploads_dir

    @property
    def covers_dir(self) -> Path:
        """获取封面目录"""
        covers = self.uploads_dir / "covers"
        covers.mkdir(parents=True, exist_ok=True)
        return covers

    @property
    def avatars_dir(self) -> Path:
        """获取头像目录"""
        avatars = self.uploads_dir / "avatars"
        avatars.mkdir(parents=True, exist_ok=True)
        return avatars

    def is_in_cache(self, path: Path) -> bool:
        """检查路径是否在缓存目录中"""
        try:
            Path(path).resolve().relative_to(self.cache_dir)
            return True
        except ValueError:
            return False

    def is_in_favorites(self, path: Path) -> bool:
        """检查路径是否在收藏夹目录中"""
        try:
            Path(path).resolve().relative_to(self.favorites_dir)
            return True
        except ValueError:
            return False

    def is_in_library(self, path: Path) -> bool:
        """检查路径是否在媒体库目录中"""
        if self.library_dir is None:
            return False
        try:
            Path(path).resolve().relative_to(self.library_dir)
            return True
        except ValueError:
            return False

    def is_in_uploads(self, path: Path) -> bool:
        """检查路径是否在上传目录中"""
        try:
            Path(path).resolve().relative_to(self.uploads_dir)
            return True
        except ValueError:
            return False


def get_storage_paths() -> StoragePaths:
    """获取存储路径管理器实例"""
    return StoragePaths.get_instance()
