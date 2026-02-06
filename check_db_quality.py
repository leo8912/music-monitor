
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def check():
    async with AsyncSessionLocal() as db:
        print("Checking FLAC/WAV songs in DB...")
        stmt = select(Song).options(selectinload(Song.sources)).where(Song.local_path.like("%.flac"))
        result = await db.execute(stmt)
        songs = result.scalars().all()
        
        print(f"Found {len(songs)} FLAC songs.")
        for s in songs[:5]:
            print(f"Song: {s.title} (ID: {s.id})")
            # print(f"  Quality Cache: {s.quality}") # Failed
            for src in s.sources:
                if src.source == 'local':
                    print(f"  Source [{src.id}]: {src.url}")
                    data = src.data_json or {}
                    print(f"  Quality: {data.get('quality', 'N/A')}")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(check())
