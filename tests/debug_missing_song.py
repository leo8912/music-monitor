
import asyncio
import sys
import os
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from app.models.artist import Artist

async def debug_missing_song():
    async with AsyncSessionLocal() as session:
        print("--- Debugging Missing Song '姑娘' ---")
        
        # 1. Search in Song table
        stmt = select(Song).options(selectinload(Song.artist), selectinload(Song.sources)).where(Song.title.ilike("%姑娘%"))
        result = await session.execute(stmt)
        songs = result.scalars().all()
        
        if not songs:
            print("❌ No song found with title containing '姑娘' in 'songs' table.")
        else:
            for s in songs:
                print(f"\n[Song ID: {s.id}]")
                print(f"  Title: {s.title}")
                print(f"  Artist: {s.artist.name if s.artist else 'None'} (Monitored: {s.artist.is_monitored if s.artist else 'N/A'})")
                print(f"  Local Path: {s.local_path}")
                print(f"  Status: {s.status}")
                print(f"  Sources: {[src.source + ':' + str(src.url) for src in s.sources]}")
                
        # 2. Search in SongSource table (orphaned sources?)
        print("\n--- Searching in SongSource table ---")
        stmt = select(SongSource).where(SongSource.url.ilike("%姑娘%"))
        result = await session.execute(stmt)
        sources = result.scalars().all()
        
        if not sources:
            print("❌ No source found with path containing '姑娘'.")
        else:
            for src in sources:
                print(f"\n[Source ID: {src.id}]")
                print(f"  Parent Song ID: {src.song_id}")
                print(f"  Source: {src.source}")
                print(f"  URL/Path: {src.url}")

        # 3. List all local songs count
        stmt = select(Song).where(Song.local_path.isnot(None))
        result = await session.execute(stmt)
        all_local = result.scalars().all()
        print(f"\nTotal Songs with local_path: {len(all_local)}")
        
if __name__ == "__main__":
    asyncio.run(debug_missing_song())
