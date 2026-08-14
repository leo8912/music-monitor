import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song
from app.services.deduplication_service import DeduplicationService
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def debug_api_response():
    print("🚀 Simulating API response for '潮汐锁定'...")
    async with AsyncSessionLocal() as db:
        # 1. 模拟 /api/library/songs 获取逻辑
        stmt = select(Song).options(
            selectinload(Song.artist),
            selectinload(Song.sources)
        ).where(Song.title.like("%潮汐锁定%"))

        result = await db.execute(stmt)
        songs = result.scalars().all()

        print(f"📊 Found {len(songs)} songs in DB.")

        # 2. 调用去重服务
        deduplicated = DeduplicationService.deduplicate_songs(songs)

        print("\n--- Deduplicated Response (Sent to Frontend) ---")
        for item in deduplicated:
            print(f"ID: {item.get('id')} | Title: {item.get('title')} | Artist: {item.get('artist')}")
            print(f"  - Cover Field: {item.get('cover')}")
            print(f"  - Source: {item.get('source')}")
            print(f"  - Available Sources: {item.get('available_sources')}")

if __name__ == "__main__":
    asyncio.run(debug_api_response())
