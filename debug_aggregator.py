
import asyncio
import logging
from app.services.music_providers import MusicAggregator

# Setup logging
logging.basicConfig(level=logging.INFO)

async def debug_search():
    aggregator = MusicAggregator()
    keyword = "我可以 蔡旻佑"
    print(f"Searching for: {keyword}")
    
    results = await aggregator.search_song(keyword, limit=5)
    
    print(f"Found {len(results)} results.")
    for i, res in enumerate(results):
        print(f"--- Result {i+1} ---")
        # Handle dict or object
        if isinstance(res, dict):
            print(f"Title: {res.get('title')}")
            print(f"Artist: {res.get('artist')}")
            print(f"Album: {res.get('album')}")
            print(f"Cover: {res.get('cover')}")
            print(f"Source: {res.get('source')}")
        else:
            print(f"Title: {getattr(res, 'title', 'N/A')}")
            print(f"Artist: {getattr(res, 'artist', 'N/A')}")
            print(f"Album: {getattr(res, 'album', 'N/A')}")
            print(f"Cover: {getattr(res, 'cover', 'N/A')}")
            print(f"Source: {getattr(res, 'source', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(debug_search())
