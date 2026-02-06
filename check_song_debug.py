
import asyncio
import os
import sys

sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def check_song():
    async with AsyncSessionLocal() as db:
        print("Searching for '一生所爱'...")
        stmt = select(Song).options(selectinload(Song.sources)).where(Song.title.like("%一生所爱%"))
        result = await db.execute(stmt)
        songs = result.scalars().all()
        
        for s in songs:
            print(f"Title: {s.title}")
            print(f"Local Path: {s.local_path}")
            for src in s.sources:
                if src.source == 'local':
                    print(f"  Source URL: {src.url}")
                    print(f"  Data JSON: {src.data_json}")
                    
if __name__ == "__main__":
    asyncio.run(check_song())
