import os
import yaml
import logging
import sys
sys.path.append(os.getcwd())
from core.config_migration import ConfigMigration

# Mock logging
logging.basicConfig(level=logging.INFO)

# Test Paths
TEST_CONFIG = "test_config_dirty.yaml"
TEST_EXAMPLE = "config.example.yaml"

# Create Dirty Config
dirty_data = {
    "notify": {
        "wecom": {
            "enabled": True,
            "corpid": "ww_correct",
            "corp_id": "ww_wrong_zombie",  # Zombie
            "agentid": "10001",
            "agent_id": "10001_wrong"      # Zombie
        }
    }
}

with open(TEST_CONFIG, 'w') as f:
    yaml.dump(dirty_data, f)

print(f"--- Created Dirty Config: {TEST_CONFIG} ---")
print(dirty_data)

# Run Migration
print("\n--- Running Migration ---")
migration = ConfigMigration(TEST_CONFIG, TEST_EXAMPLE)
changed, msg = migration.run()

print(f"\nResult: Changed={changed}, Msg={msg}")

# Check Result
with open(TEST_CONFIG, 'r') as f:
    clean_data = yaml.safe_load(f)

print("\n--- Cleaned Config ---")
print(clean_data)

wecom = clean_data['notify']['wecom']
if 'agent_id' in wecom or 'corp_id' in wecom:
    print("\n[FAIL] ZOMBIES SURVIVED!")
else:
    print("\n[PASS] ZOMBIES ELIMINATED.")
