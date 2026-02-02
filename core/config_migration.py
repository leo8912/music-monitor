"""
Configuration Migration Service
Responsible for automatically updating user configuration to match the latest schema.
"""
import os
import yaml
import logging
import shutil
import copy
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

class ConfigMigration:
    def __init__(self, config_path: str, example_path: str, template_dict: Optional[Dict[str, Any]] = None):
        self.config_path = config_path
        self.example_path = example_path
        self.template_dict = template_dict

    def run(self) -> Tuple[bool, str]:
        """
        Run the migration process.
        Returns: (changed: bool, message: str)
        """
        template_config = {}
        
        # Determine source of template
        if self.template_dict is not None:
             template_config = self.template_dict
        else:
            if not os.path.exists(self.example_path):
                return False, f"Template config not found at {self.example_path}"
            
            try:
                with open(self.example_path, 'r', encoding='utf-8') as f:
                    template_config = yaml.safe_load(f) or {}
            except Exception as e:
                return False, f"Failed to load template: {e}"

        if not os.path.exists(self.config_path):
            # If config doesn't exist, we assume it will be created by copy elsewhere.
            return False, "User config not found"

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f) or {}
            
            # 1. Create Backup
            backup_path = f"{self.config_path}.bak"
            try:
                shutil.copy2(self.config_path, backup_path)
            except Exception as e:
                logger.warning(f"Failed to create backup: {e}")

            # 2. Legacy Migration (Pre-processing)
            user_config, legacy_changed = self._migrate_legacy_keys(user_config)

            # 3. Structural Merge
            merged_config, struct_changed = self._deep_merge_defaults(user_config, template_config)

            if legacy_changed or struct_changed:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(merged_config, f, allow_unicode=True, default_flow_style=False)
                return True, "Configuration updated to latest format"
            
            return False, "No changes needed"

        except Exception as e:
            logger.error(f"Config migration failed: {e}", exc_info=True)
            return False, str(e)

    def _migrate_legacy_keys(self, config: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """
        Handle specific key renames from old versions.
        """
        changed = False
        
        # 0. Migrate 'notifications' to 'notify'
        if 'notifications' in config and config['notifications'].get('providers'):
            providers = config['notifications']['providers']
            if 'notify' not in config:
                config['notify'] = {}
            
            # WeCom
            if 'wecom' in providers and providers['wecom'].get('enabled'):
                legacy_wecom = providers['wecom']
                if 'wecom' not in config['notify']: config['notify']['wecom'] = {}
                target = config['notify']['wecom']
                target['enabled'] = legacy_wecom.get('enabled', False)
                if legacy_wecom.get('corp_id'): target['corpid'] = legacy_wecom.get('corp_id')
                if legacy_wecom.get('agent_id'): target['agentid'] = legacy_wecom.get('agent_id')
                if legacy_wecom.get('agent_secret'): target['corpsecret'] = legacy_wecom.get('agent_secret')
                changed = True

            # Telegram
            if 'telegram' in providers and providers['telegram'].get('enabled'):
                legacy_tg = providers['telegram']
                if 'telegram' not in config['notify']: config['notify']['telegram'] = {}
                target = config['notify']['telegram']
                target['enabled'] = legacy_tg.get('enabled', False)
                if legacy_tg.get('bot_token'): target['bot_token'] = legacy_tg.get('bot_token')
                if legacy_tg.get('chat_id'): target['chat_id'] = legacy_tg.get('chat_id')
                changed = True
        
        # 1. WeCom Legacy Keys (within notify.wecom)
        if config.get('notify', {}).get('wecom'):
            wecom = config['notify']['wecom']
            legacy_map = {
                'corp_id': 'corpid',
                'agent_id': 'agentid',
                'secret': 'corpsecret',
                'aes_key': 'encoding_aes_key'
            }
            keys_to_remove = []
            for old_k, new_k in legacy_map.items():
                if old_k in wecom:
                    if not wecom.get(new_k):
                        wecom[new_k] = wecom[old_k]
                        changed = True
                    keys_to_remove.append(old_k)
            
            for k in keys_to_remove:
                wecom.pop(k, None)
                changed = True
            
            # Ensure token exists if we have aes_key
            if 'encoding_aes_key' in wecom and 'token' not in wecom:
                 wecom['token'] = '' 
                 changed = True
        
        return config, changed

    def _deep_merge_defaults(self, user_val: Any, template_val: Any) -> Tuple[Any, bool]:
        """
        Recursively merge template defaults into user config.
        """
        changed = False

        if isinstance(template_val, dict):
            if not isinstance(user_val, dict):
                if user_val is None:
                    return copy.deepcopy(template_val), True
                return user_val, False 

            new_user_dict = user_val.copy()
            
            for k, v in template_val.items():
                if k not in new_user_dict:
                    new_user_dict[k] = copy.deepcopy(v)
                    changed = True
                else:
                    updated_val, sub_changed = self._deep_merge_defaults(new_user_dict[k], v)
                    if sub_changed:
                        new_user_dict[k] = updated_val
                        changed = True
            
            return new_user_dict, changed
        
        return user_val, False
