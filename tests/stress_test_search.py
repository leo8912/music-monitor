
import asyncio
import logging
import sys
import os
import time

# Add project root to path
sys.path.append(os.getcwd())

from app.services.music_providers.qqmusic_provider import QQMusicProvider

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def stress_test():
    provider = QQMusicProvider()
    keyword = "稻香 周杰伦"
    
    print(f"--- Starting Stress Test for QQMusic Search: '{keyword}' ---")
    
    success_count = 0
    total_attempts = 10
    
    for i in range(total_attempts):
        print(f"\nAttempt {i+1}/{total_attempts}...")
        start_time = time.time()
        try:
            results = await provider.search_song(keyword, limit=5)
            duration = time.time() - start_time
            
            if results:
                print(f"✅ Success! Found {len(results)} results in {duration:.2f}s")
                success_count += 1
                # print(f"   First result: {results[0].title} - {results[0].artist} (ID: {results[0].id})")
            else:
                print(f"⚠️ Returned 0 results in {duration:.2f}s")
                
        except Exception as e:
             print(f"❌ Exception: {e}")
        
        # Small delay between requests
        await asyncio.sleep(2)
        
    print(f"\n--- Summary ---")
    print(f"Success Rate: {success_count}/{total_attempts} ({success_count/total_attempts*100}%)")

if __name__ == "__main__":
    asyncio.run(stress_test())
