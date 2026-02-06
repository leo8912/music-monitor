import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from sqlalchemy import select

async def check_titles():
    async with AsyncSessionLocal() as db:
        # Check for ALL songs containing '潮汐锁定'
        stmt = select(Song).where(Song.title.like("%潮汐锁定%"))
        res = await db.execute(stmt)
        songs = res.scalars().all()
        
        print(f"🕵️ List of songs matching '潮汐锁定':")
        for s in songs:
            print(f"  ID: {s.id} | Title: {s.title} | Cover: {repr(s.cover)} | Status: {s.status}")

if __name__ == "__main__":
    asyncio.run(check_titles())
