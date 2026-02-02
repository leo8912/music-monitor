"""
配置管理模块

此模块提供统一的配置管理功能，支持多种配置源（文件、环境变量等），
实现配置的加载、验证、更新和多层级合并。

Author: music-monitor development team
"""
import os
import json
import yaml
from typing import Any, Dict, Optional, Union, TypeVar, Generic
from pathlib import Path
import logging
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


T = TypeVar('T')


class ConfigSource(Enum):
    """配置源类型"""
    YAML_FILE = "yaml_file"
    JSON_FILE = "json_file"
    ENVIRONMENT = "environment"
    DEFAULT = "default"


@dataclass
class ConfigEntry(Generic[T]):
    """配置项定义"""
    key: str
    default_value: T
    description: str = ""
    validator: Optional[callable] = None
    required: bool = False
    source: ConfigSource = ConfigSource.DEFAULT


class ConfigSchema:
    """配置模式定义"""
    
    def __init__(self):
        self.entries: Dict[str, ConfigEntry] = {}
    
    def add_entry(self, key: str, default_value: Any, description: str = "", 
                  validator: Optional[callable] = None, required: bool = False):
        """添加配置项"""
        entry = ConfigEntry(
            key=key,
            default_value=default_value,
            description=description,
            validator=validator,
            required=required
        )
        self.entries[key] = entry
        return self


class ConfigManager:
    """
    配置管理器 - 统一管理应用配置
    
    功能：
    1. 从多种源加载配置（YAML、JSON、环境变量等）
    2. 配置验证
    3. 多层级配置合并
    4. 配置更新和保存
    """
    
    def __init__(self, schema: Optional[ConfigSchema] = None):
        self.schema = schema or ConfigSchema()
        self.config: Dict[str, Any] = {}
        self._loaded_sources: Dict[str, ConfigSource] = {}
        logger.info("配置管理器初始化完成")
    
    def register_schema(self, schema: ConfigSchema):
        """注册配置模式"""
        self.schema = schema
    
    def load_from_yaml(self, filepath: Union[str, Path], merge: bool = True) -> Dict[str, Any]:
        """从YAML文件加载配置"""
        filepath = Path(filepath)
        if not filepath.exists():
            logger.warning(f"YAML配置文件不存在: {filepath}")
            return {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f)
                
            if yaml_config is None:
                yaml_config = {}
            
            # 将嵌套字典转换为扁平结构 (e.g., {"media": {"download_quality": "high"}} -> {"media.download_quality": "high"})
            flat_config = self._flatten_dict(yaml_config)
            
            if merge:
                self.config.update(flat_config)
            
            self._loaded_sources[str(filepath)] = ConfigSource.YAML_FILE
            logger.info(f"从YAML文件加载配置: {filepath}")
            return flat_config
        except Exception as e:
            logger.error(f"加载YAML配置文件失败: {filepath}, 错误: {e}")
            raise
    
    def load_from_json(self, filepath: Union[str, Path], merge: bool = True) -> Dict[str, Any]:
        """从JSON文件加载配置"""
        filepath = Path(filepath)
        if not filepath.exists():
            logger.warning(f"JSON配置文件不存在: {filepath}")
            return {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                json_config = json.load(f)
            
            # 将嵌套字典转换为扁平结构
            flat_config = self._flatten_dict(json_config)
            
            if merge:
                self.config.update(flat_config)
            
            self._loaded_sources[str(filepath)] = ConfigSource.JSON_FILE
            logger.info(f"从JSON文件加载配置: {filepath}")
            return flat_config
        except Exception as e:
            logger.error(f"加载JSON配置文件失败: {filepath}, 错误: {e}")
            raise
    
    def load_from_env(self, prefix: str = "", merge: bool = True) -> Dict[str, Any]:
        """从环境变量加载配置"""
        env_config = {}
        
        for key, value in os.environ.items():
            if prefix and key.startswith(prefix):
                # 移除前缀并转换为小写键
                config_key = key[len(prefix):].lower()
                # 将下划线分隔的键转换为点分隔（如果适用）
                config_key = config_key.replace('_', '.')
                # 尝试解析数值和布尔值
                parsed_value = self._parse_env_value(value)
                env_config[config_key] = parsed_value
            elif not prefix:
                # 如果没有前缀，则尝试匹配已注册的配置项
                config_key = key.lower()
                if config_key in self.schema.entries:
                    parsed_value = self._parse_env_value(value)
                    env_config[config_key] = parsed_value
        
        if merge:
            self.config.update(env_config)
        
        logger.info(f"从环境变量加载配置 (前缀: {prefix})")
        return env_config
    
    def _parse_env_value(self, value: str) -> Union[str, int, float, bool]:
        """解析环境变量值"""
        # 尝试解析布尔值
        if value.lower() in ('true', '1', 'yes', 'on'):
            return True
        elif value.lower() in ('false', '0', 'no', 'off', ''):
            return False
        
        # 尝试解析整数
        try:
            if '.' not in value:
                return int(value)
        except ValueError:
            pass
        
        # 尝试解析浮点数
        try:
            return float(value)
        except ValueError:
            pass
        
        # 返回字符串
        return value
    
    def load_defaults(self, merge: bool = True) -> Dict[str, Any]:
        """加载默认配置"""
        defaults = {}
        for key, entry in self.schema.entries.items():
            defaults[key] = entry.default_value
        
        if merge:
            self.config.update(defaults)
        
        logger.info("加载默认配置")
        return defaults
    
    def validate(self) -> bool:
        """验证配置"""
        errors = []
        
        for key, entry in self.schema.entries.items():
            value = self.config.get(key)
            
            # 检查必需字段
            if entry.required and value is None:
                errors.append(f"必需配置项缺失: {key}")
                continue
            
            # 运行验证器
            if entry.validator and value is not None:
                try:
                    entry.validator(value)
                except Exception as e:
                    errors.append(f"配置项验证失败 ({key}): {str(e)}")
        
        if errors:
            logger.error(f"配置验证失败: {'; '.join(errors)}")
            return False
        
        logger.info("配置验证通过")
        return True
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置配置值"""
        # 验证值（如果定义了验证器）
        if key in self.schema.entries:
            entry = self.schema.entries[key]
            if entry.validator:
                try:
                    entry.validator(value)
                except Exception as e:
                    logger.error(f"配置值验证失败 ({key}): {str(e)}")
                    raise
        
        self.config[key] = value
        logger.debug(f"设置配置: {key} = {value}")
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """获取配置区段"""
        section_config = {}
        for key, value in self.config.items():
            if key.startswith(f"{section}."):
                sub_key = key[len(section)+1:]
                section_config[sub_key] = value
        return section_config
    
    def merge_configs(self, *configs: Dict[str, Any]) -> Dict[str, Any]:
        """合并多个配置"""
        merged = {}
        for config in configs:
            merged.update(config)
        return merged
    
    def save_to_yaml(self, filepath: Union[str, Path]):
        """保存配置到YAML文件"""
        filepath = Path(filepath)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"配置已保存到YAML文件: {filepath}")
        except Exception as e:
            logger.error(f"保存YAML配置文件失败: {filepath}, 错误: {e}")
            raise
    
    def save_to_json(self, filepath: Union[str, Path]):
        """保存配置到JSON文件"""
        filepath = Path(filepath)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"配置已保存到JSON文件: {filepath}")
        except Exception as e:
            logger.error(f"保存JSON配置文件失败: {filepath}, 错误: {e}")
            raise
    
    def reload(self):
        """重新加载配置（使用上次加载的源）"""
        # 这里需要记录上次加载的配置源，暂时留空实现
        logger.info("重新加载配置")
    
    def get_loaded_sources(self) -> Dict[str, ConfigSource]:
        """获取已加载的配置源"""
        return self._loaded_sources.copy()
    
    def reset(self):
        """重置配置"""
        self.config.clear()
        self._loaded_sources.clear()
        logger.info("配置已重置")
    
    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """将嵌套字典展平为单层字典"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)


# 默认配置模式示例
def create_default_schema() -> ConfigSchema:
    """创建默认配置模式"""
    schema = ConfigSchema()
    
    # 媒体下载配置
    schema.add_entry("media.download_quality", "high", "下载音质: low, medium, high, lossless")
    schema.add_entry("media.download_directory", "./downloads", "下载目录路径")
    schema.add_entry("media.max_concurrent_downloads", 3, "最大并发下载数", 
                     lambda x: 1 <= x <= 10, required=False)
    
    # API配置
    schema.add_entry("api.timeout", 30, "API请求超时时间(秒)")
    schema.add_entry("api.retry_count", 3, "API请求重试次数")
    
    # 数据库配置
    schema.add_entry("database.url", "sqlite:///./music_monitor.db", "数据库连接URL")
    schema.add_entry("database.pool_size", 5, "连接池大小")
    
    # 日志配置
    schema.add_entry("logging.level", "INFO", "日志级别")
    schema.add_entry("logging.file_path", "./logs/app.log", "日志文件路径")
    
    # 通知配置
    schema.add_entry("notification.enabled", True, "是否启用通知", 
                     lambda x: isinstance(x, bool))
    schema.add_entry("notification.telegram.bot_token", "", "Telegram机器人令牌")
    schema.add_entry("notification.telegram.chat_id", "", "Telegram聊天ID")
    
    return schema


# 全局配置管理器实例
_config_manager = None


def get_config_manager() -> ConfigManager:
    """
    获取全局配置管理器实例
    
    Returns:
        ConfigManager: 全局配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        schema = create_default_schema()
        _config_manager = ConfigManager(schema)
        # 加载默认配置
        _config_manager.load_defaults()
    return _config_manager


def init_config(config_file: Optional[Union[str, Path]] = None, 
                env_prefix: str = "MM_") -> ConfigManager:
    """
    初始化配置管理器
    
    Args:
        config_file: 配置文件路径（可选）
        env_prefix: 环境变量前缀
        
    Returns:
        ConfigManager: 初始化后的配置管理器
    """
    manager = get_config_manager()
    
    # 加载配置文件
    if config_file:
        config_path = Path(config_file)
        if config_path.suffix.lower() in ['.yaml', '.yml']:
            manager.load_from_yaml(config_path)
        elif config_path.suffix.lower() == '.json':
            manager.load_from_json(config_path)
    
    # 加载环境变量配置
    manager.load_from_env(env_prefix)
    
    # 验证配置
    if not manager.validate():
        logger.warning("配置验证失败，但仍将继续使用配置")
    
    return manager