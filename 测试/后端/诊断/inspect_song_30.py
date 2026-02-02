import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import select
from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource

async def inspect_song_30():
    async with AsyncSessionLocal() as db:
        print("--- 歌曲 ID: 30 详细检查 (伴奏) ---")
        res = await db.execute(select(Song).where(Song.id == 30))
        song = res.scalar_one_or_none()
        if not song:
            print("Song 30 not found")
            return
            
        print(f"Title: {song.title}")
        print(f"Date: {song.publish_time}")
        
        res = await db.execute(select(SongSource).where(SongSource.song_id == 30))
        sources = res.scalars().all()
        print(f"\n--- Sources ({len(sources)}) ---")
        for s in sources:
            print(f" - Source: {s.source} | SourceID: {s.source_id}")

if __name__ == "__main__":
    asyncio.run(inspect_song_30())
