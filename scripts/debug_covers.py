import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Song).where(Song.cover.like('http%')))
        songs = result.scalars().all()
        print(f"FOUND {len(songs)} SONGS WITH HTTP COVERS IN 'Song' TABLE")
        for s in songs[:10]:
            print(f" - {s.id}: {s.title} ({s.cover})")
            
        print("\nChecking SongSource table for local sources with HTTP covers...")
        result = await db.execute(select(SongSource).where(SongSource.source == 'local', SongSource.cover.like('http%')))
        sources = result.scalars().all()
        print(f"FOUND {len(sources)} LOCAL SOURCES WITH HTTP COVERS")
        for src in sources[:10]:
            print(f" - SrcID {src.id} (SongID {src.song_id}): {src.cover}")

if __name__ == "__main__":
    asyncio.run(check())
