
import asyncio
import sys
import os
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource

async def debug_file_collision():
    async with AsyncSessionLocal() as session:
        print("--- Debugging File Collisions (Multiple Songs for same file) ---")
        
        # Join SongSource and Song
        # Group by Source URL (Local only) and count DISTINCT Song IDs
        stmt = (
            select(SongSource.url, func.count(func.distinct(SongSource.song_id)).label('song_count'))
            .where(SongSource.source == 'local')
            .group_by(SongSource.url)
            .having(func.count(func.distinct(SongSource.song_id)) > 1)
        )
        
        result = await session.execute(stmt)
        collisions = result.all()
        
        if not collisions:
            print("✅ No file collisions found (One file -> One Song).")
            return

        print(f"⚠️ Found {len(collisions)} files mapped to multiple Songs:")
        
        for row in collisions:
            url, count = row
            print(f"\nFile: {url} -> {count} Songs")
            
            # Find the songs
            sub_stmt = (
                select(Song)
                .join(SongSource)
                .where(SongSource.url == url)
                .options(selectinload(Song.sources))
            )
            songs = (await session.execute(sub_stmt)).scalars().all()
            
            for s in songs:
                 # Check if this song ONLY has this source?
                 print(f"  - Song ID: {s.id} | Title: {s.title} | Artist ID: {s.artist_id}")
                 print(f"    Local Path: {s.local_path}")
                 print(f"    Sources: {[src.id for src in s.sources]}")

if __name__ == "__main__":
    asyncio.run(debug_file_collision())
