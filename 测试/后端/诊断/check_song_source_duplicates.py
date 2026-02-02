import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import select, func
from core.database import AsyncSessionLocal
from app.models.song import SongSource

async def check_duplicates():
    async with AsyncSessionLocal() as db:
        # Find duplicates of (song_id, source, source_id)
        stmt = select(
            SongSource.song_id, 
            SongSource.source, 
            SongSource.source_id, 
            func.count(SongSource.id).label('count')
        ).group_by(
            SongSource.song_id, 
            SongSource.source, 
            SongSource.source_id
        ).having(func.count(SongSource.id) > 1)
        
        results = (await db.execute(stmt)).all()
        
        if not results:
            print("✅ No duplicates found for (song_id, source, source_id)")
            return
            
        print(f"❌ Found {len(results)} groups of duplicate sources:")
        for r in results:
            print(f"SongID: {r.song_id} | Source: {r.source} | SourceID: {r.source_id} | Count: {r.count}")
            
        # Optional: Print more details for one of them
        if results:
            first = results[0]
            detail_stmt = select(SongSource).where(
                SongSource.song_id == first.song_id,
                SongSource.source == first.source,
                SongSource.source_id == first.source_id
            )
            details = (await db.execute(detail_stmt)).scalars().all()
            print("\nDetails for first duplicate group:")
            for d in details:
                print(f"  ID: {d.id} | song_id: {d.song_id} | source: {d.source} | source_id: {d.source_id}")

if __name__ == "__main__":
    asyncio.run(check_duplicates())
