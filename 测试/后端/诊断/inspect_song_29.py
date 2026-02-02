import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import select
from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource

async def check_song_29():
    async with AsyncSessionLocal() as db:
        print("--- 歌曲 ID: 29 详细检查 ---")
        res = await db.execute(select(Song).where(Song.id == 29))
        song = res.scalar_one_or_none()
        if not song:
            print("Song 29 not found")
            return
            
        print(f"Title: {song.title}")
        print(f"Album: {song.album}")
        print(f"Date: {song.publish_time}")
        print(f"Cover: {song.cover}")
        
        res = await db.execute(select(SongSource).where(SongSource.song_id == 29))
        sources = res.scalars().all()
        print(f"\n--- Sources ({len(sources)}) ---")
        for s in sources:
            print(f" - Source: {s.source} | SourceID: {s.source_id} | Title(Data): {s.data_json}")

if __name__ == "__main__":
    asyncio.run(check_song_29())
