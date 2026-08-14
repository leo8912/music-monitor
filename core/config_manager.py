"""
配置管理器 - 集中管理应用配置

此模块提供了一个集中的配置管理系统，用于解耦配置管理逻辑，
支持多种配置源和动态配置更新。

架构变更 (2026-02-03):
- 移除了全量 YAML 依赖，转为 "内置默认值 + 数据库存储" 模式。
- config.yaml 仅用于：1. 基础设施覆盖 (Infra Overrides) 2. 迁移通知配置 (Migration)。
- 业务配置 (下载/监控/通知) 全部存储在 SystemSettings 数据库表中。

Author: music-monitor development team
"""
import os
import yaml
import logging
import copy
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, inspect

# 避免循环导入，延迟导入 Model
# from app.models.settings import SystemSettings

# 阶段 1：引入单一配置源
from core.settings import load_settings

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    配置管理器 (Hybrid Configuration Manager)

    加载顺序:
    1. 内置默认值 (Sensible Defaults)
    2. 环境变量 (Environment Variables)
    3. YAML 文件 (Infrastructure & Migration only)
    4. 数据库 (Business Settings) - 覆盖前面的业务默认值
    """

    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self._config: Dict[str, Any] = {}
        self._db_settings_loaded = False
        # 同步配置引擎缓存: 懒创建复用。旧实现每次 reload 都新建同步 engine
        # 且从不 dispose, 导致 SQLite 连接/文件句柄持续泄漏。
        self._sync_engine: Optional[Any] = None

        # 1. 加载默认配置
        self._default_config = self._get_default_config()
        self._config = copy.deepcopy(self._default_config)

        # 2. 初始加载 (不含DB，确保启动时甚至没DB也能跑)
        self.load_config(skip_db=True)

    def _get_sync_engine(self):
        """懒创建并复用同步配置引擎。

        配置读取走同步 SQLAlchemy (create_engine + Session), 而此函数会被
        reload() 反复调用 —— 每次新建 engine 会不断堆积 SQLite 连接 (文件句柄)
        且从不 dispose。改为实例级缓存: 首次调用创建, 后续复用。
        """
        from core.database import DATABASE_URL

        if self._sync_engine is None:
            self._sync_engine = create_engine(
                DATABASE_URL.replace("+aiosqlite", ""),
                pool_pre_ping=True,
            )
        return self._sync_engine

    def _get_default_config(self) -> Dict[str, Any]:
        """内置默认值：基础设施来自 AppSettings（单一 schema + env 覆盖），业务配置保持默认"""
        infra = load_settings(self.config_file).model_dump()
        business = {
            "download": {
                "max_concurrent_downloads": 3,
                "timeout": 30,
                "retry_attempts": 3,
                "quality_preference": 999,
                "sources": ["netease", "qqmusic", "kugou", "kuwo"]
            },
            "monitor": {
                "enabled": True,
                "interval": 360  # 分钟: 新歌增量监控默认每 6 小时
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
            }
        }
        return {**infra, **business}

    def load_config(self, skip_db: bool = False):
        """加载配置 (Pipeline)"""
        # 1. Reset to Defaults
        new_config = copy.deepcopy(self._default_config)

        # 2. Apply Env Vars (TODO: Implement granular env overrides if needed)
        pass

        # 3. Apply YAML (Infra Overrides & Legacy Migration)
        yaml_config = self._read_yaml()
        if yaml_config:
            # 只合并允许的基础设施字段和 Notify
            allowed_sections = ["database", "logging", "storage", "auth", "api", "notify", "monitor"] # monitor left for backward compat for now
            # 注意：Monitor users 列表如果还在 YAML，我们暂不处理，依赖 Artist 表

            self._deep_merge_allowed(new_config, yaml_config, allowed_sections)

        # 4. Apply DB (Business Settings)
        if not skip_db:
            try:
                self._load_from_db(new_config)
                # 5. Sync Migration (YAML -> DB)
                if yaml_config and "notify" in yaml_config:
                     self._sync_notify_to_db(yaml_config["notify"], new_config)

                self._db_settings_loaded = True
            except Exception as e:
                logger.warning(f"Failed to load settings from DB (Normal during init): {e}")

        self._config = new_config

        # 6. Normalize YAML (Only if DB was successfully loaded to avoid wiping config on DB error)
        if not skip_db and self._db_settings_loaded:
             self._normalize_yaml_file()

    def _read_yaml(self) -> Dict[str, Any]:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Error reading {self.config_file}: {e}")
        return {}

    def _load_from_db(self, config_ref: Dict[str, Any]):
        """从 SystemSettings 表加载业务配置"""
        from app.models.settings import SystemSettings

        # 复用懒创建的同步引擎 (避免每次 reload 新建 engine 且不 dispose 导致连接泄漏)
        engine = self._get_sync_engine()
        with Session(engine) as session:
            # check table exists
            inspector = inspect(engine)
            if not inspector.has_table("system_settings"):
                return

            settings = session.query(SystemSettings).filter_by(id=1).first()
            if not settings:
                # 初始化一行默认值
                new_settings = SystemSettings(
                    download_settings=config_ref.get("download", {}),
                    monitor_settings=config_ref.get("monitor", {}),
                    notify_settings=config_ref.get("notify", {}),
                    metadata_settings=config_ref.get("metadata", {}),
                    scheduler_settings=config_ref.get("scheduler", {})
                )
                session.add(new_settings)
                session.commit()
                settings = new_settings

            # 覆盖 Config
            if settings.download_settings:
                config_ref["download"] = settings.download_settings
            if settings.monitor_settings:
                config_ref["monitor"] = settings.monitor_settings
            if settings.notify_settings:
                config_ref["notify"] = settings.notify_settings
            if settings.metadata_settings:
                config_ref["metadata"] = settings.metadata_settings
            if settings.scheduler_settings:
                config_ref["scheduler"] = settings.scheduler_settings
            # System settings usually mostly infra, but external_url is semi-business
            # We can store 'system' in system_overrides or a specific column?
            # SystemSettings model has system_overrides.
            # But currently `load_from_db` logic below merges `system_overrides`.
            # If we want `settings.system` to be updated, we can put it in `system_overrides` dict in DB.
            # However, for structure consistency, we might want to check if `system` key exists in `system_overrides`.
            if settings.system_overrides:
                 self._deep_merge(config_ref, settings.system_overrides)

    def _sync_notify_to_db(self, yaml_notify: Dict, current_config: Dict):
        """将 YAML 中的 Notify 配置同步到 DB，然后从 YAML 中通过 Normalize 移除"""
        from app.models.settings import SystemSettings

        # 1.标准化 YAML Keys (Legacy -> New snake_case)
        # WeCom
        if "wecom" in yaml_notify:
            wc = yaml_notify["wecom"]
            # Map legacy keys
            if "corpid" in wc and "corp_id" not in wc:
                wc["corp_id"] = wc.pop("corpid")
            if "agentid" in wc and "agent_id" not in wc:
                wc["agent_id"] = wc.pop("agentid")
            if "corpsecret" in wc and "secret" not in wc:
                wc["secret"] = wc.pop("corpsecret")
            if "agent_secret" in wc and "secret" not in wc:
                wc["secret"] = wc.pop("agent_secret")

        # Telegram - usually standard, but check just in case

        engine = self._get_sync_engine()
        with Session(engine) as session:
            settings = session.query(SystemSettings).filter_by(id=1).first()
            if settings:
                # Merge existing DB notify with YAML notify (YAML wins for migration)
                # Ensure we deep merge so we don't lose other providers if one is missing in YAML
                existing = settings.notify_settings or {}
                merged_notify = self._deep_merge(existing, yaml_notify)

                settings.notify_settings = merged_notify
                session.commit()
                # 更新当前内存配置
                current_config["notify"] = merged_notify

    def _normalize_yaml_file(self):
        """重写 config.yaml，仅保留基础设施配置和注释 (Preserves Comments via Template)"""
        current_yaml = self._read_yaml()

        # 提取 Infrastructure Values (如果为空则留空，或使用当前内存中的值?)
        # 最好使用 current_yaml 中的值，因为那是用户刚才可能填写的
        # 如果 current_yaml 中没有，则留空字符串或默认值

        def get_val(section, key, default):
            if section in current_yaml and key in current_yaml[section]:
                return current_yaml[section][key]
            return default

        # Template Construction
        # 数据库
        db = current_yaml.get('database', {})
        db_url = db.get('url', 'sqlite+aiosqlite:///music_monitor.db')
        db_echo = str(db.get('echo', False)).lower()
        db_pool = db.get('pool_size', 5)
        db_max = db.get('max_overflow', 10)

        # 日志
        log = current_yaml.get('logging', {})
        log_level = log.get('level', 'INFO')
        log_file = log.get('file', 'logs/application.log')
        log_max_bytes = log.get('max_bytes', 10485760)
        log_backup = log.get('backup_count', 5)

        # 存储
        storage = current_yaml.get('storage', {})
        lib_dir = storage.get('library_dir', '/library')
        cache_dir = storage.get('cache_dir', '/audio_cache')
        fav_dir = storage.get('favorites_dir', '/favorites')
        max_cache = storage.get('max_cache_size', 10737418240)
        retention = storage.get('retention_days', 180)

        # 认证
        auth = current_yaml.get('auth', {})
        auth_enabled = str(auth.get('enabled', True)).lower()
        auth_user = auth.get('username', 'admin')
        auth_pass = auth.get('password', 'password')
        auth_secret = auth.get('secret_key', 'CHANGE_ME')

        # API
        api = current_yaml.get('api', {})
        api_timeout = api.get('timeout', 30)

        # System
        sys_conf = current_yaml.get('system', {})
        ext_url = sys_conf.get('external_url', 'http://localhost:8000')

        # 构建带注释的 YAML 字符串
        yaml_content = f"""# ==============================================================================
# Music Monitor 配置文件
# ==============================================================================
# 💡 说明:
# 本系统采用 "数据库 + 配置文件" 的混合配置模式。
# 1. 基础设施 (数据库、日志、路径): 必须在此文件或环境变量中配置。
# 2. 业务功能 (下载、监控、通知): 请启动后在网页端 "设置" 页面进行配置。
#
# 👇 以下配置均为 基础设施配置 (Infrastructure)
# ==============================================================================

# --- 1. HTTP API 服务 ---
api:
  rate_limit:
    requests_per_minute: 60  # 限流: 每分钟请求数
    burst_size: 10          # 限流: 突发允许数
  timeout: {api_timeout}               # 全局 API 超时 (秒)

# --- 2. 安全认证 (Auth) ---
auth:
  enabled: {auth_enabled}
  username: "{auth_user}"         # 默认管理员用户
  password: "{auth_pass}"      # 默认管理员密码 (请修改!)
  secret_key: "{auth_secret}"   # JWT 签名密钥 (⚠️ 必须修改以保证安全)
  algorithm: "HS256"
  access_token_expire_minutes: 30
  refresh_token_expire_days: 7

# --- 3. 数据库 (Database) ---
database:
  # 默认使用 SQLite。如需 MySQL/PG，请修改 URL。
  # 格式: sqlite+aiosqlite:///路径 或 mysql+aiomysql://user:pass@host/db
  url: "{db_url}"
  echo: {db_echo}               # 是否打印 SQL (调试用)
  pool_size: {db_pool}
  max_overflow: {db_max}

# --- 4. 日志 (Logging) ---
logging:
  level: "{log_level}"             # DEBUG, INFO, WARNING, ERROR
  format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  file: "{log_file}"
  max_bytes: {log_max_bytes}
  backup_count: {log_backup}

# --- 5. 存储路径 (Storage) ---
storage:
  # 资料库: 存放您确认收藏的高质量文件 (只读，不自动删除)
  library_dir: "{lib_dir}"

  # 缓存: 存放自动下载和试听的临时文件 (会自动清理)
  cache_dir: "{cache_dir}"

  # 收藏: 点击红心后的文件存放处
  favorites_dir: "{fav_dir}"

  # 缓存策略
  auto_cache_enabled: true
  max_cache_size: {max_cache}
  cleanup_threshold: 0.8
  retention_days: {retention}

# --- 6. 系统/外部链接 (System) ---
system:
    external_url: "{ext_url}" # 用于生成分享链接

# ==============================================================================
# 🚀 迁移辅助 (Migration Helper)
#
# 如果通过 Config 迁移旧版通知设置，可以在此填写。
# 启动一次成功导入数据库后，推荐在 UI 中管理。
# ==============================================================================
"""
        # Always preserve/update 'notify' section in config.yaml as requested
        current_notify = self._config.get("notify")
        if current_notify:
            import yaml
            # Deep copy to avoid mutating memory config
            notify_dump = copy.deepcopy(current_notify)
            if "wecom" in notify_dump:
                wc = notify_dump["wecom"]
                # Convert Internal Keys (corp_id) -> Legacy YAML Keys (corpid)
                if "corp_id" in wc:
                    wc["corpid"] = wc.pop("corp_id")
                if "agent_id" in wc:
                    wc["agentid"] = wc.pop("agent_id")
                if "secret" in wc:
                    wc["corpsecret"] = wc.pop("secret")
                # Ensure no zombies
                for z in ["agent_id", "corp_id", "secret", "aes_key"]:
                     wc.pop(z, None)

            # Dump notify block as standard yaml appended to the end
            notify_block = yaml.dump({"notify": notify_dump}, default_flow_style=False, allow_unicode=True)
            yaml_content += "\n" + notify_block

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
        except Exception as e:
            logger.error(f"Failed to normalize config.yaml: {e}")

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """深度合并"""
        result = copy.deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _deep_merge_allowed(self, base: Dict, override: Dict, allowed_keys: list):
        """仅合并允许的顶层 Key"""
        for key in allowed_keys:
            if key in override:
                 if isinstance(base.get(key), dict) and isinstance(override[key], dict):
                     base[key] = self._deep_merge(base[key], override[key])
                 else:
                     base[key] = override[key]

    # --- Public Accessors ---
    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def reload(self):
        """重新加载 (包括 DB sync)"""
        self.load_config(skip_db=False)

    def update(self, updates: Dict[str, Any]):
        """更新内存配置 (不持久化到 YAML)"""
        self._config = self._deep_merge(self._config, updates)


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None

def _detect_config_path() -> str:
    """Detect configuration file path"""
    # Priority: Env -> Container -> Local
    if os.getenv("CONFIG_FILE"):
        return os.getenv("CONFIG_FILE")

    paths = [
        "/config/config.yaml",
        "config/config.yaml",
        "config.yaml"
    ]

    for p in paths:
        if os.path.exists(p):
            return p

    return "config.yaml"

CONFIG_FILE_PATH = _detect_config_path()

def get_config_manager() -> ConfigManager:
    global _config_manager  # noqa: PLW0603 - 单例惰性初始化惯用法
    if _config_manager is None:
        _config_manager = ConfigManager(config_file=CONFIG_FILE_PATH)
    return _config_manager

def reload_config() -> bool:
    get_config_manager().reload()
    return True

