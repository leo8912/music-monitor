import asyncio
import sys
import os

# Adapt path for imports
sys.path.append(os.getcwd())

from app.services.music_providers.qqmusic_provider import QQMusicProvider

async def test_qq_cover():
    provider = QQMusicProvider()
    keyword = "我不要原谅你 宿羽阳"
    print(f"Searching for: {keyword}")
    
    songs = await provider.search_song(keyword, limit=3)
    if not songs:
        print("No songs found via search.")
        return

    for song in songs:
        print(f"\n--- Song: {song.title} ({song.artist}) ---")
        print(f"ID: {song.id}")
        print(f"Album: {song.album}")
        print(f"Search Result Cover: {song.cover_url}")
        
        # Try fetching details
        print("Fetching details...")
        metadata = await provider.get_song_metadata(song.id)
        if metadata:
            print(f"Failed to get metadata? {not metadata}")
            print(f"Metadata Cover: {metadata.get('cover_url')}")
            print(f"Metadata Album: {metadata.get('album')}")
        else:
            print("Failed to get metadata.")

if __name__ == "__main__":
    asyncio.run(test_qq_cover())
