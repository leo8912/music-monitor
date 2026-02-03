
import asyncio
import logging
import sys
import os
sys.path.append(os.getcwd())
from app.services.song_management_service import SongManagementService
from core.database import AsyncSessionLocal
from app.repositories.song import SongRepository

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_redownload():
    async with AsyncSessionLocal() as db:
        repo = SongRepository(db)
        # Find a song to redownload
        # Custom query with eager load
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.models.song import Song
        stmt = select(Song).options(selectinload(Song.sources), selectinload(Song.artist)).limit(1)
        res = await db.execute(stmt)
        songs = res.scalars().all()
        if not songs:
            print("No songs found in DB")
            return

        song = songs[0]
        print(f"Testing redownload for song: {song.title} (ID: {song.id})")
        
        # Determine source
        source = "netease"
        source_id = "123456" # Dummy, or try to find from existing source
        if song.sources:
            s = song.sources[0]
            source = s.source
            source_id = s.source_id
            print(f"Using source: {source}:{source_id}")
        
        service = SongManagementService()
        try:
            success = await service.redownload_song(
                db=db,
                song_id=song.id,
                source=source,
                source_id=source_id,
                quality=999,
                title=song.title,
                artist=song.artist.name if song.artist else "Unknown"
            )
            print(f"Redownload result: {success}")
        except Exception as e:
            print(f"Redownload failed with exception: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_redownload())
