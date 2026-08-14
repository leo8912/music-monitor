"""应用配置：单一配置源（pydantic-settings）。

阶段 1 引入，取代 core/config.py 的散乱全局 dict 与 core/config_migration.py 的
模板合并。职责边界（与 SystemSettings 表互补）：
- 基础设施（api/auth/database/logging/storage/system）：来自 YAML + 环境变量
- 业务配置（download/monitor/metadata/scheduler/notify）：仍存 SystemSettings 表

环境变量优先级高于 YAML。database.url 支持 DATABASE_URL 别名以兼容现有测试与部署。
"""
import os
from typing import Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RateLimit(BaseModel):
    requests_per_minute: int = 60
    burst_size: int = 10


class ApiConfig(BaseModel):
    rate_limit: RateLimit = Field(default_factory=RateLimit)
    timeout: int = 30


class AuthConfig(BaseModel):
    enabled: bool = True
    username: str = "admin"
    password: str = "password"
    secret_key: str = "CHANGE_ME"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    avatar: Optional[str] = None


class DatabaseConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    # 别名兼容现有 DATABASE_URL 环境变量（测试与部署均依赖）
    url: str = Field(
        default="sqlite+aiosqlite:///config/music_monitor.db",
        validation_alias="DATABASE_URL",
    )
    echo: bool = False


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "logs/application.log"
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5


class StorageConfig(BaseModel):
    library_dir: str = "/library"
    cache_dir: str = "/audio_cache"
    favorites_dir: str = "/favorites"
    max_cache_size: int = 10 * 1024 * 1024 * 1024
    cleanup_threshold: float = 0.8
    retention_days: int = 180


class SystemConfig(BaseModel):
    external_url: str = ""


class RedisConfig(BaseModel):
    """任务队列/实时通道依赖的内置 Redis。

    本地开发/测试默认关闭 (enabled=false) → 队列降级为进程内 inline 执行；
    生产 Docker 环境 (MM_REDIS__ENABLED=true) → 使用 arq + unixsocket。
    """
    enabled: bool = False
    # 优先使用 unixsocket (Docker 内置 redis, 不暴露端口)
    unix_socket: str = "/tmp/redis.sock"
    # 备选 TCP 连接串 (本地带 Redis 或外部 Redis 时使用)
    url: str = "redis://127.0.0.1:6379/0"


class WeComConfig(BaseModel):
    enabled: bool = False
    token: str = ""
    encoding_aes_key: str = ""
    corp_id: str = ""
    secret: str = ""
    agent_id: str = ""


class TelegramConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


class NotifyConfig(BaseModel):
    enabled: bool = False
    wecom: WeComConfig = Field(default_factory=WeComConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)


class AppSettings(BaseSettings):
    """基础设施配置。env 前缀 MM_，嵌套分隔符 __（如 MM_DATABASE__ECHO）。"""

    model_config = SettingsConfigDict(
        env_prefix="MM_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    api: ApiConfig = Field(default_factory=ApiConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    notify: NotifyConfig = Field(default_factory=NotifyConfig)


# 与 core/config_manager._detect_config_path 保持一致的路径优先级
def detect_config_path() -> str:
    if os.getenv("CONFIG_FILE"):
        return os.getenv("CONFIG_FILE")
    for p in ("/config/config.yaml", "config/config.yaml", "config.yaml"):
        if os.path.exists(p):
            return p
    return "config.yaml"


def load_settings(config_file: str | None = None) -> AppSettings:
    """加载配置：内置默认 < 环境变量 < YAML（仅覆盖模型声明的段）。"""
    settings = AppSettings()
    path = config_file or detect_config_path()
    if not os.path.exists(path):
        return settings
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    # 只取模型声明过的顶层段，未知段（如遗留 monitor 用户列表）丢弃
    infra = {k: v for k, v in data.items() if k in AppSettings.model_fields}
    if not infra:
        return settings
    merged = {**settings.model_dump(), **infra}
    return AppSettings.model_validate(merged)
