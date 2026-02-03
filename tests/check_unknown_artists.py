
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from core.database import AsyncSessionLocal
from app.models.song import Song
from app.models.artist import Artist

async def check_unknowns():
    async with AsyncSessionLocal() as db:
        # 1. 检查没有关联歌手的歌曲 (artist_id is NULL)
        stmt_null = select(Song).where(Song.artist_id.is_(None), Song.local_path.isnot(None))
        res_null = await db.execute(stmt_null)
        null_songs = res_null.scalars().all()
        print(f"Found {len(null_songs)} songs with artist_id=NULL and local_path.")
        
        # 2. 检查歌手名为 "未知" 变体的歌曲
        stmt_name = select(Song).options(selectinload(Song.artist)).join(Artist).where(
            Artist.name.in_(["未知歌手", "Unknown Artist", "Unknown", "未知"]),
            Song.local_path.isnot(None)
        )
        res_name = await db.execute(stmt_name)
        named_songs = res_name.scalars().all()
        print(f"Found {len(named_songs)} songs with 'Unknown' variants in name and local_path.")
        
        # 3. 打印一些样例
        print("\nDetail Samples (First 20 local songs):")
        stmt_sample = select(Song).options(selectinload(Song.artist)).where(Song.local_path.isnot(None)).limit(20)
        res_sample = await db.execute(stmt_sample)
        samples = res_sample.scalars().all()
        for s in samples:
            a_name = s.artist.name if s.artist else "NULL_ARTIST"
            print(f"  - [{s.title}] Artist: [{a_name}] Path: {s.local_path}")

from sqlalchemy.orm import selectinload # Make sure imported
if __name__ == "__main__":
    import sqlalchemy.orm # Ensure available
    asyncio.run(check_unknowns())

if __name__ == "__main__":
    asyncio.run(check_unknowns())
