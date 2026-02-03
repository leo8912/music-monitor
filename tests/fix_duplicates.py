
import asyncio
import sys
import os
from sqlalchemy import select, func, delete, text

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import SongSource

async def fix_duplicates():
    async with AsyncSessionLocal() as session:
        print("--- Cleaning up duplicate local sources ---")
        
        # 1. Find duplicates based on (song_id, source, url)
        # We group by these fields and count > 1
        stmt = (
            select(SongSource.song_id, SongSource.source, SongSource.url, func.count(SongSource.id).label('count'))
            .where(SongSource.source == 'local')
            .group_by(SongSource.song_id, SongSource.source, SongSource.url)
            .having(func.count(SongSource.id) > 1)
        )
        
        result = await session.execute(stmt)
        duplicates = result.all()
        
        total_removed = 0
        
        if not duplicates:
            print("✅ No duplicate local sources found.")
            return

        print(f"⚠️ Found {len(duplicates)} groups of duplicates.")
        
        for row in duplicates:
            song_id, source, url, count = row
            print(f"  - Song {song_id} | Path: {url} | Count: {count}")
            
            # Fetch all matching records
            sub_stmt = select(SongSource).where(
                SongSource.song_id == song_id,
                SongSource.source == source,
                SongSource.url == url
            ).order_by(SongSource.id.desc()) # Keep latest? Or check if IDs vary widely
            
            records = (await session.execute(sub_stmt)).scalars().all()
            
            # Keep the first one (latest ID), delete the rest
            to_keep = records[0]
            to_delete = records[1:]
            
            print(f"    Keeping ID: {to_keep.id}. Deleting {len(to_delete)} records...")
            
            for r in to_delete:
                await session.delete(r)
                
            total_removed += len(to_delete)
            
        await session.commit()
        print(f"\n✅ Cleanup complete. Removed {total_removed} duplicate sources.")

if __name__ == "__main__":
    asyncio.run(fix_duplicates())
