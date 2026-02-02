"""
Config配置管理 - 应用配置加载和管理

此文件负责：
- 应用配置的加载和保存
- 配置文件迁移和版本升级
- 安全密钥管理
- 监控用户配置管理

Author: music-monitor development team
"""
import yaml
import secrets
import re
import logging
import os
from core.config_migration import ConfigMigration

logger = logging.getLogger(__name__)

config = {}

# Path Detection Logic
if os.path.exists("/config/config.yaml"):
    CONFIG_FILE_PATH = "/config/config.yaml"
elif os.path.exists("config.yaml"):
    CONFIG_FILE_PATH = "config.yaml"
elif os.path.exists("config/config.yaml"):
    CONFIG_FILE_PATH = "config/config.yaml"
else:
    # Fallback or create new
    CONFIG_FILE_PATH = "/config/config.yaml" if os.path.isdir("/config") else "config.yaml"

logger.info(f"Using Configuration File: {CONFIG_FILE_PATH}")


# Example Config Path Detection
if os.path.exists("config.example.yaml"):
    EXAMPLE_CONFIG_PATH = "config.example.yaml"
elif os.path.exists("/app/config.example.yaml"):
    EXAMPLE_CONFIG_PATH = "/app/config.example.yaml"
else:
    # Fallback lookup (e.g. relative to this file)
    _rel_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.example.yaml")
    # core/config.py -> core -> app? -> root? 
    # __file__ = d:/code/music-monitor/core/config.py
    # dirname = core
    # dirname = music-monitor
    # join config.example.yaml
    # Actually locally usage:
    _local_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.example.yaml")
    if os.path.exists(_local_root):
        EXAMPLE_CONFIG_PATH = _local_root
    else:
        EXAMPLE_CONFIG_PATH = "config.example.yaml" 

def load_config():
    if not os.path.exists(CONFIG_FILE_PATH):
        # Return default or empty if not found (or copy example in main)
        return {}
    with open(CONFIG_FILE_PATH, "r", encoding='utf-8') as f:
        return yaml.safe_load(f)

def migrate_and_save_config():
    """Run auto-migration using ConfigMigration service."""
    try:
        # 1. Load Example Template
        template_dict = {}
        if os.path.exists(EXAMPLE_CONFIG_PATH):
             try:
                with open(EXAMPLE_CONFIG_PATH, "r", encoding='utf-8') as f:
                    template_dict = yaml.safe_load(f) or {}
             except Exception as e:
                 logger.error(f"Failed to load config template: {e}")
        else:
             logger.warning(f"Template config not found at {EXAMPLE_CONFIG_PATH}, skipping structural migration.")

        # 2. Apply Environment-Specific Defaults (Overrides)
        # Only if 'storage' is in template, we might want to ensure acceptable defaults for this env
        if 'storage' in template_dict:
             # If NOT inside /config (container), use relative paths for safer dev defaults
             if not CONFIG_FILE_PATH.startswith("/config"):
                 if template_dict['storage'].get('cache_dir') == '/audio_cache':
                     template_dict['storage']['cache_dir'] = 'audio_cache'
                 if template_dict['storage'].get('favorites_dir') == '/favorites':
                     template_dict['storage']['favorites_dir'] = 'favorites'

        # 3. Run Migration
        migration = ConfigMigration(CONFIG_FILE_PATH, EXAMPLE_CONFIG_PATH, template_dict=template_dict)
        changed, msg = migration.run()
        
        if changed:
            logger.info(f"Config migration: {msg}")
            return True, msg
        return False, msg

    except Exception as e:
        logger.error(f"Config migration failed: {e}")
        return False, str(e)

def ensure_security_config():
    """Ensure secret_key is secure and not default."""
    try:
        if not os.path.exists(CONFIG_FILE_PATH):
            return secrets.token_urlsafe(32), False
            
        with open(CONFIG_FILE_PATH, "r", encoding='utf-8') as f:
            content = f.read()
        
        # Check current secret
        match = re.search(r'secret_key:\s*["\']?([^"\']+)["\']?', content)
        if match:
            current_secret = match.group(1).strip()
            # If default or weak
            if current_secret in ["secret_key_for_session_encryption", "default_secret_key", "CHANGE_THIS_TO_RANDOM_SECRET", "CHANGE_THIS_SECRET_KEY"]:
                new_secret = secrets.token_urlsafe(32)
                logger.warning(f"Detected weak secret_key. Rotated to new random key.")
                
                # Replace in content (preserve whitespace/comments)
                new_content = re.sub(
                    r'(secret_key:\s*)(["\']?)([^"\']+)(["\']?)', 
                    f'\\1"{new_secret}"', 
                    content
                )
                
                with open(CONFIG_FILE_PATH, "w", encoding='utf-8') as f:
                    f.write(new_content)
                
                return new_secret, True
            return current_secret, False
    except Exception as e:
        logger.error(f"Security config check failed: {e}")
        # Return random temp secret
        return secrets.token_urlsafe(32), False

def add_monitored_user(source: str, user_id: str, name: str, avatar: str = None) -> bool:
    """Add a new user to monitor config and save."""
    try:
        # 1. Update In-Memory Config
        if not config.get('monitor'): config['monitor'] = {}
        if not config['monitor'].get(source): config['monitor'][source] = {'enabled': True, 'users': []}
        
        users = config['monitor'][source].get('users')
        if users is None: 
            users = []
            config['monitor'][source]['users'] = users
            
        # Check duplicate
        for u in users:
            if str(u.get('id')) == str(user_id):
                return False # Already exists
        
        new_entry = {'id': str(user_id), 'name': name}
        if avatar: new_entry['avatar'] = avatar
            
        users.append(new_entry)
        config['monitor'][source]['users'] = users
        
        # 2. Save to File
        with open(CONFIG_FILE_PATH, "r", encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
            
        if not data.get('monitor'): data['monitor'] = {}
        if not data['monitor'].get(source): data['monitor'][source] = {'enabled': True, 'users': []}
        
        # Ensure we don't duplicate in file if it desynced
        file_users = data['monitor'][source].get('users')
        if file_users is None:
             file_users = []
             data['monitor'][source]['users'] = file_users
             
        exists = False
        for u in file_users:
            if str(u.get('id')) == str(user_id):
                exists = True
                break
        
        if not exists:
            file_entry = {'id': str(user_id), 'name': name}
            if avatar: file_entry['avatar'] = avatar
            file_users.append(file_entry)
            data['monitor'][source]['users'] = file_users
            
            with open(CONFIG_FILE_PATH, "w", encoding='utf-8') as f:
                yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)
                
        return True
    except Exception as e:
        logger.error(f"Failed to add monitored user: {e}")
        return False
