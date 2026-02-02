
import asyncio
import logging
import sys
import os
import traceback
from unittest.mock import MagicMock, AsyncMock, patch

# Add project root to path
sys.path.append(os.getcwd())

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_redownload():
    print("--- Starting Redownload Logic Test ---")
    
    try:
        from app.services.library import LibraryService
        from app.models.song import Song
        
        # Mock Song Object
        class MockSong:
            def __init__(self):
                self.id = 1
                self.title = "Test Song"
                self.artist = MagicMock()
                self.artist.name = "Test Artist"
                self.local_path = "tests/old_file.mp3"
                self.status = "PENDING"
                self.cover = None
        
        # Setup DB Mock
        db = AsyncMock()
        
        # Create dummy old file
        if not os.path.exists("tests"): os.makedirs("tests")
        with open("tests/old_file.mp3", "w", encoding='utf-8') as f:
            f.write("dummy content")
            
        # Patch Dependencies
        # 1. Patch DownloadService in the MODULE where it is defined, accessed by import
        #    Since LibraryService imports it dynamically, we patch 'app.services.download_service.DownloadService'
        
        with patch('app.services.download_service.DownloadService') as MockDSClass:
            # Configure Mock Instance
            mock_ds_instance = MockDSClass.return_value
            mock_ds_instance.cache_dir = "tests"
            mock_ds_instance._convert_traditional_to_simplified = lambda x: x
            mock_ds_instance.get_audio_url = AsyncMock(return_value={
                "url": "http://mock.url/file", "br": 999, "size": 100
            })
            mock_ds_instance.download_file = AsyncMock(return_value=True)

            print(f"Mock DS Instance configured: {mock_ds_instance}")

            # 2. Patch SongRepository
            mock_repo_instance = MagicMock()
            mock_song_data = MockSong()
            mock_repo_instance.get = AsyncMock(return_value=mock_song_data)
            
            with patch('app.services.library.SongRepository', return_value=mock_repo_instance):
                
                # 3. Patch ScraperService (imported inside method)
                #    Since it's imported inside redownload_song, we patch 'app.services.scraper.ScraperService' 
                #    assuming that's where it comes from.
                
                with patch('app.services.scraper.ScraperService') as MockScraperClass:
                    mock_scraper_instance = MockScraperClass.return_value
                    mock_scraper_instance.scrape_and_apply = AsyncMock(return_value=True)

                    # Instantiate Library Service
                    service = LibraryService()
                    
                    print("Calling redownload_song...")
                    success = await service.redownload_song(
                        db, 1, "qqmusic", "001"
                    )
                    
                    print(f"Result: {success}")
                    
                    # Verifications
                    if success:
                        print("✅ Function returned True")
                    else:
                        print("❌ Function returned False")
                        
                    # Check Call Args
                    mock_ds_instance.get_audio_url.assert_awaited()
                    print("✅ get_audio_url awaited")
                    
                    mock_ds_instance.download_file.assert_awaited()
                    print("✅ download_file awaited")
                    
                    expected_file = "tests/Test Artist - Test Song.flac"
                    if mock_song_data.local_path.replace("\\", "/") == expected_file.replace("\\", "/"):
                         print("✅ DB local_path updated")
                    else:
                         print(f"❌ DB local_path mismatch: {mock_song_data.local_path}")
                         
                    mock_scraper_instance.scrape_and_apply.assert_awaited()
                    print("✅ ScraperService awaited")
                    
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_redownload())
