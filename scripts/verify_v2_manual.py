
import asyncio
import sys
import os
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import async_engine as engine, Base
from app.models.artist import Artist, ArtistSource
from app.models.song import Song, SongSource
from app.services.library import LibraryService
from app.services.subscription import SubscriptionService

async def verify_flow():
    print(">>> Starting V2 Schema Validation...")
    
    # 1. Setup DB Session
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as db:
        # 0. Initialize DB (Create Tables)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        # Clear Data
        print(">>> Cleaning DB...")
        try:
            await db.execute(text("DELETE FROM song_sources"))
            await db.execute(text("DELETE FROM songs"))
            await db.execute(text("DELETE FROM artist_sources"))
            await db.execute(text("DELETE FROM artists"))
            await db.commit()
        except Exception:
            await db.rollback()
            # Tables might be empty/new, ignore delete error if needed, but create_all should fix "no such table"
            pass
        
        # 2. Add Artist (Simulate Frontend Call)
        print(">>> Adding Artist (Jay Chou)...")
        # Mocking a known ID for testing (e.g. QQ Music ID for Jay Chou: 4558)
        # Assuming SubscriptionService.add_artist can handle this
        added = await SubscriptionService.add_artist(
            db, 
            name="周杰伦", 
            source="qqmusic", 
            artist_id="4558",
            avatar="http://mock.avatar/jay.jpg"
        )
        assert added == True, "Add Artist failed"
        
        # Verify Artist Created
        stmt = select(Artist).where(Artist.name == "周杰伦")
        artist = (await db.execute(stmt)).scalars().first()
        assert artist is not None, "Artist not found in DB"
        print(f"    [OK] Logical Artist Created: {artist.name} (ID: {artist.id})")
        
        # Verify Sources
        stmt = select(ArtistSource).where(ArtistSource.artist_id == artist.id)
        sources = (await db.execute(stmt)).scalars().all()
        print(f"    [OK] Linked Sources: {[s.source for s in sources]}")
        assert len(sources) >= 1, "No sources linked"
        
        # Verify Avatar persistence in ArtistSource
        # Note: In our add_artist logic, we search mock aggregator.
        # But we haven't mocked the aggregator for add_artist (only for refresh_artist below).
        # SubscriptionService uses aggregator.search_artist.
        # Since we might not have network, the "add" might fallback to Manual create.
        # If Manual create, avatar is set from input.
        # Our input was (source="qqmusic", artist_id="4558") and NO avatar param.
        # So it might be empty if network fails.
        # Let's verify column exists at least.
        print(f"    [OK] Linked Source 0 Avatar: {sources[0].avatar}")
        # If we want to test avatar saving, we should provide it in add_artist or mock search.
        # Let's provide it in add_artist call above to be sure.
        
        # 3. Trigger Refresh (Simulate Background Task / Frontend Trigger)
        print(">>> Refreshing Library (Fetching Songs)...")
        lib_service = LibraryService()
        
        # Mock Aggregator to ensure we test DB logic, not Network/API health
        from unittest.mock import MagicMock, patch
        from app.services.music_providers.base import SongInfo
        
        mock_song = SongInfo(
                id="song_1",
                # site_id removed
                source="qqmusic",
                title="Mock Song Title",
                artist="Jay Chou",
                album="Mock Album",
                duration=300,
                cover_url="http://example.com/cover.jpg",
                # year removed
                publish_time="2023-01-01",
                # url removed from init
        )
        # Dynamically add attributes expected by LibraryService
        mock_song.url = "http://example.com/audio.mp3"
        mock_song.quality = "128k"
        
        mock_songs = [mock_song]
        
        # Patch the class where it is used. library.py imports MusicAggregator inside the method?
        # library.py line 620: from app.services.music_providers.aggregator import MusicAggregator
        # We need to patch 'app.services.library.MusicAggregator' if it was imported at top level
        # But since it is imported INSIDE, we patch 'app.services.music_providers.aggregator.MusicAggregator'
        
        
        with patch('app.services.music_providers.aggregator.MusicAggregator') as MockAggClass:
            mock_agg = MockAggClass.return_value
            # Make it awaitable
            f = asyncio.Future()
            f.set_result(mock_songs)
            mock_agg.get_artist_songs_from_all_sources.return_value = f
            
            # Also mock search for add_artist (already done safely)
            
            count = await lib_service.refresh_artist(db, artist_name="周杰伦")
            print(f"    [OK] Refreshed {count} songs (Mocked)")
        
        # 4. Verify Songs
        stmt = select(Song).where(Song.artist_id == artist.id)
        songs = (await db.execute(stmt)).scalars().all()
        assert len(songs) > 0, "No songs fetched (Mocked)"
        print(f"    [OK] Found {len(songs)} songs in DB")
        
        # Check Song Sources
        sample_song = songs[0]
        stmt = select(SongSource).where(SongSource.song_id == sample_song.id)
        s_sources = (await db.execute(stmt)).scalars().all()
        print(f"    [OK] Sample Song '{sample_song.title}' has {len(s_sources)} sources: {[s.source for s in s_sources]}")
        assert len(s_sources) > 0, "Song has no sources"
        
        # 5. Verify Metadata
        print(f"    [OK] Sample Metadata: Album='{sample_song.album}', Cover='{sample_song.cover[:20]}...'")
        
    print(">>> All Validations Passed!")

if __name__ == "__main__":
    from sqlalchemy.ext.asyncio import AsyncSession
    try:
        asyncio.run(verify_flow())
    except Exception as e:
        print(f"❌ Verification Failed: {e}")
        import traceback
        traceback.print_exc()
