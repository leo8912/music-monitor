
import asyncio
import logging
import os
import sys

# Ensure import
sys.path.append(os.getcwd())
from core.audio_downloader import audio_downloader

# Logging
logging.basicConfig(level=logging.INFO)

async def verify_cross():
    print("--- Verifying Cross-Source Smart Match ---")
    
    # Test Case:
    # Song: 我偏要吻你破碎 - 宿羽阳
    # Source: tencent (Fails even with search)
    # Expected: Should switch to netease and succeed
    
    bad_id = "bad_tencent_id"
    title = "我偏要吻你破碎"
    artist = "宿羽阳"
    source = "tencent"
    
    # Clean cache
    cache_path = os.path.join("audio_cache", "宿羽阳 - 我偏要吻你破碎.flac")
    if os.path.exists(cache_path): os.remove(cache_path)
    cache_path_mp3 = os.path.join("audio_cache", "宿羽阳 - 我偏要吻你破碎.mp3")
    if os.path.exists(cache_path_mp3): os.remove(cache_path_mp3)

    print(f"Testing download with Source={{source}} (Fails natively)")
    
    result = await audio_downloader.download(
        source=source,
        song_id=bad_id,
        title=title,
        artist=artist,
        quality=320 # Try high quality
    )
    
    if result:
        print("\n✅ Download Success!")
        print(f"Path: {result['local_path']}")
        print(f"Quality: {result['quality']}")
        print(f"Format: {result['format']}")
        print("🎉 SUCCESS: Cross-source match likely worked!")
    else:
        print("\n❌ Download Failed (Cross-source match failed)")

if __name__ == "__main__":
    asyncio.run(verify_cross())
