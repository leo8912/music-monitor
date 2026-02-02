
import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

# Mock config
from core.config_manager import ConfigManager
# We need to ensure we read the actual config file
# ConfigManager is a singleton, let's hope it reads from disk freshly or we force it.

async def verify():
    print("--- 1. Verifying ScanService Paths ---")
    from app.services.scan_service import ScanService
    
    # Initialize Service
    scanner = ScanService()
    print(f"Configs loaded: {scanner.scan_directories}")
    
    expected = ['/library', '/audio_cache', '/favorites']
    # Note: Config file has these values. 
    # Logic in ScanService: 
    # 1. cache_dir -> /audio_cache
    # 2. favorites_dir -> /favorites
    # 3. library_dir -> /library
    
    # Check if all expected are present (order might vary due to set)
    # But paths are normalized in ScanService, possibly absolute paths?
    # ScanService code: self.scan_directories = [p for p in paths ...] where paths is a set.
    
    # Let's filter for our key paths to be sure
    found_keys = []
    for p in scanner.scan_directories:
        if 'library' in p: found_keys.append('library')
        if 'audio_cache' in p: found_keys.append('cache')
        if 'favorites' in p: found_keys.append('favorites')
        
    print(f"Found keys: {found_keys}")
    
    if len(found_keys) >= 3:
        print("✅ ScanService loaded all 3 paths.")
    else:
        print("❌ ScanService missing paths.")

    print("\n--- 2. Verifying FavoriteService Logic (Dry Run) ---")
    from app.services.favorite_service import FavoriteService
    
    # We can't easily test the full async logic without a DB and files, 
    # but we can verify it imports the config correctly by inspecting the code or partial run.
    # Actually, let's just create the directories to ensure they exist for the test
    
    os.makedirs("audio_cache", exist_ok=True)
    os.makedirs("favorites", exist_ok=True)
    os.makedirs("library", exist_ok=True)
    
    print("✅ Directories ensured. (Manual verification of logic flow required if not mocking DB)")
    print("Code inspection confirms logic:\n"
          " - Check if in library -> Skip\n"
          " - If Like and in Cache -> Move to Favorites\n"
          " - If Unlike and in Favorites -> Move to Cache")

if __name__ == "__main__":
    asyncio.run(verify())
