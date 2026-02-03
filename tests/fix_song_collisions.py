
import asyncio
import sys
import os
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource

async def fix_song_collisions():
    async with AsyncSessionLocal() as session:
        print("--- Fixing Song Collisions (Merging Duplicate Songs) ---")
        
        # 1. Find Collisions
        stmt = (
            select(SongSource.url, func.count(func.distinct(SongSource.song_id)))
            .where(SongSource.source == 'local')
            .group_by(SongSource.url)
            .having(func.count(func.distinct(SongSource.song_id)) > 1)
        )
        
        collisions = (await session.execute(stmt)).all()
        print(f"⚠️ Found {len(collisions)} files with multiple songs.")
        
        removed_songs_count = 0
        
        for row in collisions:
            url, _ = row
            # Fetch all songs for this file
            sub_stmt = (
                select(Song)
                .join(SongSource)
                .where(SongSource.url == url)
                .options(selectinload(Song.sources))
            )
            songs = (await session.execute(sub_stmt)).scalars().all()
            
            # Determine Winner
            # Criteria: Has local_path > Valid Artist > id desc?
            winner = None
            losers = []
            
            # Sort by quality criteria
            # We want the one that ScanService just created/updated correctly.
            # Usually the one with local_path set.
            
            working_songs = sorted(songs, key=lambda s: (
                1 if s.local_path else 0, # Prefer local_path set
                1 if s.artist_id else 0,  # Prefer known artist
                s.id # Prefer newer ID
            ), reverse=True)
            
            winner = working_songs[0]
            losers = working_songs[1:]
            
            print(f"  File: {os.path.basename(url)}")
            print(f"    Winner: ID {winner.id} [{winner.title}] (Path: {winner.local_path})")
            
            for loser in losers:
                print(f"    Deleting Loser: ID {loser.id} [{loser.title}] (Path: {loser.local_path})")
                await session.delete(loser)
                removed_songs_count += 1
        
        await session.commit()
        print(f"\n✅ Merge complete. Removed {removed_songs_count} duplicate songs.")

if __name__ == "__main__":
    asyncio.run(fix_song_collisions())
