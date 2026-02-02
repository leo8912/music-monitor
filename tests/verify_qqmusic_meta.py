
import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.services.music_providers.qqmusic_provider import QQMusicProvider

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_qqmusic_metadata():
    provider = QQMusicProvider()
    
    song_mid = "003aAYrm3GE0Ac" # 稻香
    keyword = "稻香"
    
    print(f"\n--- Testing Metadata Fetch for ID: {song_mid} ---")
    meta = await provider.get_song_metadata(song_mid)
    print(f"Meta Result: {meta}")
    
    print(f"\n--- Testing Search for: {keyword} ---")
    search_results = await provider.search_song(keyword, limit=5)
    print(f"Found {len(search_results)} results")
    for song in search_results:
        print(f"ID: {song.id}")
        print(f"Title: {song.title}")
        print(f"Artist: {song.artist}")
        print(f"Album: {song.album}")
        print(f"Date: {song.publish_time}")
        print(f"Cover: {song.cover_url}")
        print("-" * 20)
        
        if str(song.id) == str(song_mid):
            print("    [MATCHED TARGET ID in Search]")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_qqmusic_metadata())
