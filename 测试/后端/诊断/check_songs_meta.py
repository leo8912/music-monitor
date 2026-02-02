import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import select
from core.database import AsyncSessionLocal
from app.models.song import Song

async def check_specific_songs():
    async with AsyncSessionLocal() as db:
        titles = ["潮汐锁定", "请允许我成为你的夏季", "踏破风的少年", "暗恋是一个人的事", "我不要原谅你"]
        print("--- 核心曲目元数据核查 ---")
        for title in titles:
            res = await db.execute(select(Song).where(Song.artist_id == 5, Song.title.like(f"%{title}%")))
            songs = res.scalars().all()
            for s in songs:
                print(f"ID: {s.id} | Title: {s.title} | Date: {s.publish_time} | HasCover: {bool(s.cover)} | Album: {s.album}")

if __name__ == "__main__":
    asyncio.run(check_specific_songs())
