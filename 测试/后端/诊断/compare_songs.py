import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app.services.music_providers import MusicAggregator

async def run():
    aggregator = MusicAggregator()
    artist_ids = {'qqmusic': '000GBnpV1IcEfl', 'netease': '12459252'}
    
    # Check Netease specifically
    print("--- Netease Data ---")
    netease_songs = await aggregator.providers[0].get_artist_songs(artist_ids['netease'], limit=100)
    for s in netease_songs:
        if "我不要原谅你" in s.title:
            print(f"Title: {s.title} | Album: {s.album} | Date: {s.publish_time} | ID: {s.id}")
            
    print("\n--- QQ Music Data ---")
    qq_songs = await aggregator.providers[1].get_artist_songs(artist_ids['qqmusic'], limit=100)
    for s in qq_songs:
        if "我不要原谅你" in s.title:
            print(f"Title: {s.title} | Album: {s.album} | Date: {s.publish_time} | ID: {s.id}")

if __name__ == "__main__":
    asyncio.run(run())
