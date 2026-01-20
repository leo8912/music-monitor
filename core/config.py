import yaml
import secrets
import re
import logging
import os

logger = logging.getLogger(__name__)

config = {}

# Path Detection Logic
if os.path.exists("/config/config.yaml"):
    CONFIG_FILE_PATH = "/config/config.yaml"
elif os.path.exists("config.yaml"):
    CONFIG_FILE_PATH = "config.yaml"
else:
    # Fallback or create new
    CONFIG_FILE_PATH = "/config/config.yaml" if os.path.isdir("/config") else "config.yaml"

def load_config():
    if not os.path.exists(CONFIG_FILE_PATH):
        # Return default or empty if not found (or copy example in main)
        return {}
    with open(CONFIG_FILE_PATH, "r", encoding='utf-8') as f:
        return yaml.safe_load(f)

def migrate_and_save_config():
    """Check for legacy config keys and migrate them to new format."""
    try:
        if not os.path.exists(CONFIG_FILE_PATH):
            return False, "Config not found"

        with open(CONFIG_FILE_PATH, "r", encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        changed = False

        # 1. WeCom Legacy Keys
        if 'notify' in data and 'wecom' in data['notify']:
            wecom = data['notify']['wecom']
            legacy_map = {
                'corp_id': 'corpid',
                'agent_id': 'agentid',
                'secret': 'corpsecret',
                'aes_key': 'encoding_aes_key'
            }
            
            keys_to_remove = []
            for old_k, new_k in legacy_map.items():
                if old_k in wecom:
                    # If new key missing, migrate value
                    if not wecom.get(new_k):
                        wecom[new_k] = wecom[old_k]
                        changed = True
                    # If both exist, we can safely remove old one to clean up
                    # But maybe user wants to keep it?
                    # Let's clean it up to enforce new standard.
                    keys_to_remove.append(old_k)
            
            for k in keys_to_remove:
                wecom.pop(k, None)
                changed = True
                
            # Ensure token exists if we have aes_key
            if 'token' not in wecom:
                 wecom['token'] = '' # Placeholder
                 changed = True

        # 2. Storage Defaults
        if 'storage' not in data:
            data['storage'] = {
                'cache_dir': '/audio_cache' if CONFIG_FILE_PATH.startswith("/config") else 'audio_cache',
                'favorites_dir': '/favorites' if CONFIG_FILE_PATH.startswith("/config") else 'favorites',
                'library_path': '',
                'retention_days': 180,
                'auto_cache_enabled': True
            }
            changed = True
            
        # 3. Global Defaults
        if 'global' in data:
            if 'external_url' not in data['global']:
                data['global']['external_url'] = ''
                changed = True

        if changed:
            with open(CONFIG_FILE_PATH, "w", encoding='utf-8') as f:
                yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)
            logger.info("Configuration automatically migrated to new format.")
            return True, "Migrated"
            
        return False, "No changes"

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
            if current_secret in ["secret_key_for_session_encryption", "default_secret_key", "CHANGE_THIS_TO_RANDOM_SECRET"]:
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
