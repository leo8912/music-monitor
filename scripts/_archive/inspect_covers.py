import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def inspect_songs():
    print("🔍 Inspecting Database for Cover Links...")
    async with AsyncSessionLocal() as db:
        # 1. 查找最近 5 首被治愈的歌曲
        stmt = select(Song).options(selectinload(Song.sources)).order_by(Song.last_enrich_at.desc()).limit(5)
        result = await db.execute(stmt)
        songs = result.scalars().all()

        print("\n--- Recent Healed Songs ---")
        for s in songs:
            print(f"ID: {s.id} | Title: {s.title} | Cover: {s.cover}")
            for src in s.sources:
                print(f"  - Source: {src.source} | Cover: {src.cover}")
                if src.data_json:
                    print(f"    - data_json cover: {src.data_json.get('cover')}")

        # 2. 搜索特定歌曲 "潮汐锁定"
        print("\n--- Searching for '潮汐锁定' ---")
        stmt = select(Song).options(selectinload(Song.sources)).where(Song.title.like("%潮汐锁定%"))
        result = await db.execute(stmt)
        songs = result.scalars().all()
        for s in songs:
            print(f"ID: {s.id} | Title: {s.title} | Artist ID: {s.artist_id} | Cover: {s.cover}")
            for src in s.sources:
                print(f"  - Source: {src.source} | Cover: {src.cover}")

if __name__ == "__main__":
    asyncio.run(inspect_songs())
