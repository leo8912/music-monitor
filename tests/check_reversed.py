
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from core.database import AsyncSessionLocal
from app.models.song import Song
from app.models.artist import Artist

async def check_reversed():
    async with AsyncSessionLocal() as db:
        # 查找标题包含 "陈楚生" 或 "姑娘" 的歌曲
        stmt = select(Song).options(selectinload(Song.artist)).where(
            (Song.title.like("%陈楚生%")) | (Song.title.like("%姑娘%"))
        )
        result = await db.execute(stmt)
        songs = result.scalars().all()
        
        print(f"Candidate songs for flipped metadata:")
        for s in songs:
            a_name = s.artist.name if s.artist else "None"
            print(f"  ID: {s.id}, Title: {s.title}, Artist: {a_name}, Path: {s.local_path}")

if __name__ == "__main__":
    asyncio.run(check_reversed())
