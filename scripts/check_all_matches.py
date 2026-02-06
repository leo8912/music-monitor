import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song
from sqlalchemy import select

async def check_all_matches():
    async with AsyncSessionLocal() as db:
        stmt = select(Song).where(Song.title.like("%潮汐锁定%"))
        res = await db.execute(stmt)
        songs = res.scalars().all()
        
        print(f"📊 Total matching songs: {len(songs)}")
        for s in songs:
            print(f"  [{s.id}] {s.title} | Artist ID: {s.artist_id}")
            print(f"    Cover: {s.cover}")
            print(f"    Status: {s.status}")

if __name__ == "__main__":
    asyncio.run(check_all_matches())
