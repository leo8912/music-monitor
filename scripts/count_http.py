import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from sqlalchemy import select, func

async def count_http_covers():
    async with AsyncSessionLocal() as db:
        # Song table
        stmt = select(func.count()).select_from(Song).where(Song.cover.like("http%"))
        res = await db.execute(stmt)
        song_count = res.scalar()
        
        # SongSource table
        stmt = select(func.count()).select_from(SongSource).where(SongSource.cover.like("http%"))
        res = await db.execute(stmt)
        source_count = res.scalar()
        
        print(f"📊 Songs with HTTP cover: {song_count}")
        print(f"📊 SongSources with HTTP cover: {source_count}")
        
        if song_count > 0:
            print("\n🔍 Sample songs with HTTP cover:")
            stmt = select(Song).where(Song.cover.like("http%")).limit(5)
            res = await db.execute(stmt)
            for s in res.scalars():
                print(f"  - [{s.id}] {s.title} ({s.status}): {s.cover}")

if __name__ == "__main__":
    asyncio.run(count_http_covers())
