
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from core.database import AsyncSessionLocal
from app.models.song import Song
from app.services.deduplication_service import DeduplicationService

async def verify_dedup():
    async with AsyncSessionLocal() as db:
        # 查找 "姑娘" 相关的歌曲
        stmt = select(Song).options(selectinload(Song.artist), selectinload(Song.sources)).where(
            Song.title.like("%姑娘%")
        )
        result = await db.execute(stmt)
        songs = result.scalars().all()
        
        # 模拟 API 去重
        deduped = DeduplicationService.deduplicate_songs(songs)
        
        print(f"Deduped Result count: {len(deduped)}")
        for item in deduped:
            print(f"Title: {item.get('title')}")
            print(f"  Artist: {item.get('artist')}")
            print(f"  Local Path: {item.get('local_path')}")
            print(f"  Created At: {item.get('created_at')}")
            print(f"  Publish Time: {item.get('publish_time')}")
            print(f"  Source: {item.get('source')}")
            print(f"  Available Sources: {item.get('availableSources')}")

if __name__ == "__main__":
    asyncio.run(verify_dedup())
