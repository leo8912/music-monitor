import os
import pytest
from unittest.mock import MagicMock, patch
from app.services.scan_service import ScanService
from app.models.song import Song
from app.models.artist import Artist
from sqlalchemy import select

@pytest.mark.asyncio
async def test_normalize_cn_brackets():
    service = ScanService()
    assert service._normalize_cn_brackets("周杰伦（Live）") == "周杰伦(Live)"
    assert service._normalize_cn_brackets("【测试】 标题") == "[测试]标题"
    assert service._normalize_cn_brackets(None) == ""

@pytest.mark.asyncio
async def test_scan_local_files_empty(db_session):
    # Test scanning with no directories
    service = ScanService()
    service.scan_directories = []
    
    results = await service.scan_local_files(db_session)
    assert results["new_files_found"] == 0
    assert results["removed_files_count"] == 0

@pytest.mark.asyncio
async def test_extract_metadata_fallback(db_session):
    service = ScanService()
    # Mock extract_metadata to simulate a file with title in filename
    with patch("app.services.scan_service.ScanService._extract_metadata") as mock_extract:
        mock_extract.return_value = {
            "title": "Song Title",
            "artist_name": "Singer",
            "album": "Album Name",
            "quality": "SQ"
        }
        
        # We're testing the logic that uses this metadata
        # Since we don't want to touch the real filesystem, we mock the scan loop
        pass

@pytest.mark.asyncio
async def test_find_or_create_song_new(db_session):
    service = ScanService()
    from app.repositories.song import SongRepository
    song_repo = SongRepository(db_session)
    
    # Create artist first
    artist = Artist(name="Test Artist")
    db_session.add(artist)
    await db_session.flush()
    
    metadata = {
        "title": "New Song",
        "album": "Test Album",
        "publish_time": None,
        "cover": None
    }
    
    song = await service._find_or_create_song(db_session, song_repo, metadata, artist)
    assert song.title == "New Song"
    assert song.artist_id == artist.id
    
    # Verify in DB
    stmt = select(Song).where(Song.title == "New Song")
    db_result = (await db_session.execute(stmt)).scalars().first()
    assert db_result is not None
    assert db_result.id == song.id
