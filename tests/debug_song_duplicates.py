
import asyncio
import sys
import os
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource

async def debug_song_duplicates():
    async with AsyncSessionLocal() as session:
        print("--- Debugging Song Duplicates ---")
        
        # Group by title and count
        stmt = (
            select(Song.title, func.count(Song.id).label('count'))
            .group_by(Song.title)
            .having(func.count(Song.id) > 1)
        )
        
        result = await session.execute(stmt)
        duplicates = result.all()
        
        if not duplicates:
            print("✅ No duplicate song titles found.")
            # Check total count
            cnt = await session.scalar(select(func.count(Song.id)))
            print(f"Total Songs: {cnt}")
            return

        print(f"⚠️ Found {len(duplicates)} titles with multiple Song records:")
        
        for row in duplicates:
            title, count = row
            print(f"\nTitle: '{title}' (Count: {count})")
            
            # Get details
            sub_stmt = select(Song).options(selectinload(Song.artist)).where(Song.title == title)
            songs = (await session.execute(sub_stmt)).scalars().all()
            
            for s in songs:
                print(f"  - ID: {s.id} | Artist: {s.artist.name if s.artist else 'None'} | Status: {s.status}")
                print(f"    Local Path: {s.local_path}")
                print(f"    Created: {s.created_at}")
                # Check sources
                src_stmt = select(SongSource).where(SongSource.song_id == s.id)
                sources = (await session.execute(src_stmt)).scalars().all()
                print(f"    Sources: {[src.source for src in sources]}")

if __name__ == "__main__":
    asyncio.run(debug_song_duplicates())
