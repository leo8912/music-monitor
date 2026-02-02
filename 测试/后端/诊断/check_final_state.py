import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import select
from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource

async def check_database():
    async with AsyncSessionLocal() as db:
        print("--- 数据库歌曲检查 (宿羽阳) ---")
        stmt = select(Song).where(Song.artist_id == 5) # 宿羽阳 ID is 5
        songs = (await db.execute(stmt)).scalars().all()
        
        print(f"总计找到 {len(songs)} 首歌曲。")
        
        target_title = "我不要原谅你"
        print(f"\n--- 包含 '{target_title}' 的数据库项 ---")
        for s in songs:
            if target_title in s.title:
                print(f"ID: {s.id} | Title: {s.title} | Date: {s.publish_time} | Cover: {bool(s.cover)} | Album: {s.album}")
                
        print("\n--- 缺失元数据的歌曲 (无封面且无日期) ---")
        missing_count = 0
        for s in songs:
            if not s.cover and (not s.publish_time or s.publish_time.year <= 1970):
                print(f"ID: {s.id} | Title: {s.title} | Date: {s.publish_time}")
                missing_count += 1
        print(f"总计 {missing_count} 首缺失元数据。")

if __name__ == "__main__":
    asyncio.run(check_database())
