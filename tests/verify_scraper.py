
import asyncio
import logging
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
sys.path.append(os.getcwd())

from app.services.scraper import ScraperService
from app.services.music_providers.base import SongInfo
# Mock objects
class MockSong:
    def __init__(self):
        self.id = 1
        self.title = "稻香"
        self.artist = "周杰伦"
        self.album = ""
        self.publish_time = ""
        self.cover_url = ""
        self.lyrics = ""
        self.local_path = "tests/test.flac"
        self.source = "unknown"
        self.source_id = ""

async def test_scraper():
    # Setup Mocks
    aggregator = MagicMock()
    metadata_service = MagicMock()
    
    # Mock Provider
    provider = MagicMock()
    provider.get_song_metadata = AsyncMock(return_value={
        'title': '稻香',
        'artist': '周杰伦',
        # Intentionally missing album/date/cover to trigger backfill
    })
    
    # Mock Search Result for Backfill
    search_res = SongInfo(
        title="稻香",
        artist="周杰伦",
        album="魔杰座",
        source="qqmusic",
        id="003HxOK24HGHQcT", # Different ID
        cover_url="http://example.com/cover.jpg",
        publish_time="2008-10-15"
    )
    provider.search_song = AsyncMock(return_value=[search_res])
    aggregator.get_provider.return_value = provider
    
    metadata_service.fetch_cover_data = AsyncMock(return_value=b"fake_image_data")
    
    # Setup Service
    scraper = ScraperService(aggregator, metadata_service)
    
    # Mock DB Session
    db = AsyncMock()
    
    # Mock Song
    song = MockSong()
    
    # Run Scrape
    print("--- Starting Scrape Test ---")
    success = await scraper.scrape_and_apply(db, song, "qqmusic", "12345")
    
    print(f"Scrape Success: {success}")
    print(f"Song Metadata After Scrape:")
    print(f"  Title: {song.title}")
    print(f"  Artist: {song.artist}")
    print(f"  Album: {song.album} (Expected: 魔杰座)")
    print(f"  Date: {song.publish_time} (Expected: 2008-10-15)")
    print(f"  Cover: {song.cover_url} (Expected: http://example.com/cover.jpg)")
    
    if song.album == "魔杰座" and song.publish_time == "2008-10-15":
        print("✅ Backfill logic worked!")
    else:
        print("❌ Backfill logic failed.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_scraper())
