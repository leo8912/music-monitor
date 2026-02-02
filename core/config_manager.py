"""
配置管理器 - 集中管理应用配置

此模块提供了一个集中的配置管理系统，用于解耦配置管理逻辑，
支持多种配置源和动态配置更新。

Author: music-monitor development team
"""
import os
import yaml
from typing import Any, Dict, Optional
from pathlib import Path
import logging


class ConfigManager:
    """
    配置管理器
    提供集中化的配置管理功能
    """
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self._config: Dict[str, Any] = {}
        self._default_config = self._get_default_config()
        self.load_config()
        
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "storage": {
                "cache_dir": "audio_cache",
                "favorite_dir": "favorites",
                "media_dir": "media",
                "max_cache_size": 10 * 1024 * 1024 * 1024,  # 10GB
                "cleanup_threshold": 0.8  # 达到80%时清理
            },
            "download": {
                "max_concurrent_downloads": 3,
                "timeout": 30,
                "retry_attempts": 3,
                "quality_preference": 999,  # 最高质量
                "sources": ["netease", "qqmusic", "kugou", "kuwo"]
            },
            "metadata": {
                "enable_lyrics": True,
                "enable_cover": True,
                "enable_album": True,
                "lyrics_priority": ["plugin", "kugou", "qqmusic"],
                "cover_priority": ["plugin"],
                "album_priority": ["plugin"]
            },
            "scheduler": {
                "check_interval_minutes": 60,
                "sync_interval_hours": 24,
                "cleanup_interval_hours": 24
            },
            "api": {
                "rate_limit": {
                    "requests_per_minute": 60,
                    "burst_size": 10
                },
                "timeout": 30
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "logs/application.log",
                "max_bytes": 10 * 1024 * 1024,  # 10MB
                "backup_count": 5
            },
            "database": {
                "url": "sqlite+aiosqlite:///./music_monitor.db",
                "echo": False,
                "pool_size": 5,
                "max_overflow": 10
            },
            "auth": {
                "enabled": False,
                "secret_key": "your-secret-key-here",
                "algorithm": "HS256",
                "access_token_expire_minutes": 30,
                "refresh_token_expire_days": 7
            },
            "notifications": {
                "enabled": False,
                "providers": {
                    "wecom": {
                        "enabled": False,
                        "corp_id": "",
                        "agent_secret": "",
                        "agent_id": ""
                    },
                    "telegram": {
                        "enabled": False,
                        "bot_token": "",
                        "chat_id": ""
                    }
                }
            }
        }
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = yaml.safe_load(f)
                    if loaded_config:
                        # 合并默认配置和加载的配置
                        self._config = self._deep_merge(self._default_config, loaded_config)
                    else:
                        self._config = self._default_config.copy()
            except Exception as e:
                logging.warning(f"Failed to load config from {self.config_file}: {e}")
                self._config = self._default_config.copy()
        else:
            # 如果配置文件不存在，使用默认配置
            self._config = self._default_config.copy()
    
    def save_config(self):
        """保存配置到文件"""
        try:
            # 确保目录存在
            config_path = Path(self.config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            logging.error(f"Failed to save config to {self.config_file}: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的嵌套键"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """设置配置值，支持点号分隔的嵌套键"""
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def update(self, updates: Dict[str, Any]):
        """批量更新配置"""
        self._config = self._deep_merge(self._config, updates)
    
    def reload(self):
        """重新加载配置文件"""
        old_config = self._config.copy()
        self.load_config()
        return old_config != self._config  # 返回是否发生改变
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """深度合并两个字典"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get_storage_config(self) -> Dict[str, Any]:
        """获取存储配置"""
        return self.get("storage", {})
    
    def get_download_config(self) -> Dict[str, Any]:
        """获取下载配置"""
        return self.get("download", {})
    
    def get_metadata_config(self) -> Dict[str, Any]:
        """获取元数据配置"""
        return self.get("metadata", {})
    
    def get_scheduler_config(self) -> Dict[str, Any]:
        """获取调度器配置"""
        return self.get("scheduler", {})
    
    def get_api_config(self) -> Dict[str, Any]:
        """获取API配置"""
        return self.get("api", {})
    
    def get_database_config(self) -> Dict[str, Any]:
        """获取数据库配置"""
        return self.get("database", {})
    
    def get_auth_config(self) -> Dict[str, Any]:
        """获取认证配置"""
        return self.get("auth", {})
    
    def get_notification_config(self) -> Dict[str, Any]:
        """获取通知配置"""
        return self.get("notifications", {})


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


from core.config import CONFIG_FILE_PATH

def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_file=CONFIG_FILE_PATH)
    return _config_manager


def get_config_value(key: str, default: Any = None) -> Any:
    """便捷函数：获取配置值"""
    return get_config_manager().get(key, default)


def set_config_value(key: str, value: Any):
    """便捷函数：设置配置值"""
    get_config_manager().set(key, value)


def reload_config() -> bool:
    """便捷函数：重新加载配置"""
    return get_config_manager().reload()