import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def sync_all_sources():
    print("🚀 Syncing all Source covers from Song table...")
    async with AsyncSessionLocal() as db:
        # 查找所有已经本地化的歌曲
        stmt = select(Song).options(selectinload(Song.sources)).where(Song.cover.like("/uploads/%"))
        result = await db.execute(stmt)
        songs = result.scalars().all()
        
        print(f"📊 Found {len(songs)} songs with localized covers.")
        
        count = 0
        for s in songs:
            for src in s.sources:
                if src.cover != s.cover:
                    src.cover = s.cover
                    count += 1
        
        await db.commit()
        print(f"✅ Synced {count} SongSource records.")

if __name__ == "__main__":
    asyncio.run(sync_all_sources())
