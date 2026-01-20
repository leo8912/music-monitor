
import asyncio
import logging
import os
import sys

# Ensure imports
sys.path.append(os.getcwd())
from core.audio_downloader import audio_downloader

logging.basicConfig(level=logging.INFO)

async def debug_single_song():
    print("--- Debugging Single Song Failure ---")
    
    # Failed song from previous run
    # Name: 我偏要吻你破碎 (000ByIXJ44SsAE)
    # Artist: 宿羽阳
    # Source: tencent (based on ID format, but let's assume it was passed as such)
    
    # Note: 00xxxx is usually Tencent (QQ Music) ID.
    # The previous log showed "Original ID (002qqgZN2RmQBo) failed".
    # Wait, the log said "Source: netease" for ID 333..., but what about these?
    # diagnose_backfill_live printed:
    # Processing: 我偏要吻你破碎 - 宿羽阳 (Source: qqmusic likely?)
    
    # I need to check the source. 
    # Let's try to search/match manually.
    
    title = "我偏要吻你破碎"
    artist = "宿羽阳"
    source = "qqmusic" # Guessing based on previous context of "宿羽阳" being in both
    
    # 1. Search Manual
    print(f"\n1. Testing Smart Match Search for: {title} {artist} (Source: {source})")
    new_id = await audio_downloader._search_match(source, title, artist)
    print(f"   Result: {new_id}")
    
    if new_id:
        print(f"\n2. Testing URL Fetch with New ID: {new_id}")
        info = await audio_downloader._fetch_audio_url(source, new_id, quality=320)
        if info:
            print(f"   ✅ URL Found: {info.url}")
        else:
            print("   ❌ URL Fetch Failed for New ID")
            
    else:
        print("\n   ❌ Search Failed. Trying Netease source?")
        new_id_ne = await audio_downloader._search_match("netease", title, artist)
        print(f"   Netease Search Result: {new_id_ne}")

if __name__ == "__main__":
    asyncio.run(debug_single_song())
