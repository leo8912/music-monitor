import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app.services.music_providers import MusicAggregator

async def analyze_dedup():
    aggregator = MusicAggregator()
    
    test_cases = [
        ("我不要原谅你", "宿羽阳"),
        ("我不要原谅你（伴奏）", "宿羽阳"),
        ("我不要原谅你 (Inst.)", "宿羽阳"),
        ("潮汐锁定", "宿羽阳"),
        ("潮汐锁定 (Tidal Locked)", "宿羽阳"),
    ]
    
    print("--- Dedup Key Test ---")
    keys = []
    for title, artist in test_cases:
        key = aggregator._generate_dedup_key(title, artist)
        keys.append(key)
        print(f"[{title}] -> {key}")
    
    # Check if original and instrumental are different
    if keys[0] != keys[1]:
        print("\n✅ Original and Instrumental separated!")
    else:
        print("\n❌ Original and Instrumental still merged!")
        
    # Check if different suffixes of instrumental are same (optional, but good to know)
    if keys[1] == keys[2]:
        print("✅ Different instrumental annotations merged (Good)")

if __name__ == "__main__":
    asyncio.run(analyze_dedup())
