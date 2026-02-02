import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def run():
    async with AsyncSessionLocal() as db:
        stmt = (
            select(Song)
            .options(selectinload(Song.sources))
            .where(Song.artist_id == 1, Song.title.contains('我不要原谅你'))
        )
        songs = (await db.execute(stmt)).scalars().all()
        
        print(f"Found {len(songs)} songs matching '我不要原谅你' in DB:")
        for s in songs:
            sources = [f"{src.source}:{src.source_id}" for src in s.sources]
            print(f"ID: {s.id} | Title: {s.title} | Date: {s.publish_time} | Sources: {sources} | Status: {s.status}")

if __name__ == "__main__":
    asyncio.run(run())
