import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.enrichment_service import EnrichmentService
from app.services.smart_merger import SongMetadata
from app.models.song import Song

@pytest.mark.asyncio
async def test_enrich_song_uses_smart_merger():
    """验证 enrich_song 使用 SmartMerger 进行合并"""
    
    # Mock dependencies
    mock_db = AsyncMock()
    mock_aggregator = AsyncMock() # Not used directly if we mock metadata_service, but service inits it
    
    with patch("app.services.enrichment_service.AsyncSessionLocal", return_value=mock_db), \
         patch("app.services.enrichment_service.MusicAggregator", return_value=mock_aggregator), \
         patch("app.services.enrichment_service.MetadataService") as MockMetaService, \
         patch("app.services.enrichment_service.SmartMerger") as MockSmartMerger:
         
        # Setup Mocks
        service = EnrichmentService()
        
        # Inject mocked internal services if needed (or rely on them being instantiated)
        # Assuming EnrichmentService instantiates them or we patch the instance methods
        
        # Mock song data
        mock_song = MagicMock(spec=Song)
        mock_song.id = "123"
        mock_song.title = "Test Song"
        mock_song.artist = MagicMock()
        mock_song.artist.name = "Test Artist"
        mock_song.album = "Old Album"
        mock_song.cover = "old_cover.jpg"
        mock_song.publish_time = "1970-01-01"
        mock_song.sources = []
        
        mock_db.__aenter__.return_value.get.return_value = mock_song
        
        # Mock MetadataService return
        mock_meta_instance = MockMetaService.return_value
        online_meta = SongMetadata(
            title="Test Song", 
            artist="Test Artist", 
            album="New Album", 
            cover_url="new_cover.jpg",
            publish_time="2023-01-01",
            confidence=1.0
        )
        mock_meta_instance.get_best_match_metadata = AsyncMock(return_value=online_meta)
        
        # Mock SmartMerger behavior
        mock_merger_instance = MockSmartMerger.return_value
        merged_meta = SongMetadata(
            title="Test Song", 
            artist="Test Artist", 
            album="New Album", # Overwritten
            cover_url="new_cover.jpg", # Overwritten
            publish_time="2023-01-01" # Overwritten
        )
        mock_merger_instance.merge.return_value = merged_meta
        
        # Mock download cover to avoid real net request
        service._download_cover = AsyncMock(return_value=("/uploads/covers/new.jpg", "/tmp/new.jpg"))
        service._write_tags_to_file = AsyncMock()
        
        # Execute
        await service.enrich_song("123")
        
        # Verify
        # 1. Verify MetadataService was called
        mock_meta_instance.get_best_match_metadata.assert_called_with("Test Song", "Test Artist")
        
        # 2. Verify SmartMerger was called
        # We need to reconstruct what 'local' metadata would look like
        # mock_merger_instance.merge.assert_called() 
        # Checking arguments might be tricky with objects, just checking call count is good for Red phase
        assert mock_merger_instance.merge.call_count == 1
        
        # 3. Verify Song object was updated
        assert mock_song.album == "New Album"
        assert mock_song.publish_time == "2023-01-01"
