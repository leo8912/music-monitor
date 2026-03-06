import asyncio
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from core.database import AsyncSessionLocal
from app.models.artist import Artist
from app.models.song import Song

async def test_song_status():
    async with AsyncSessionLocal() as db:
        # 统计宿羽阳(ID: 4)的歌曲状态
        stmt = select(Song.status, func.count(Song.id)).where(Song.artist_id == 4).group_by(Song.status)
        result = await db.execute(stmt)
        print(f"\nSong status distribution for Artist ID 4 (宿羽阳):")
        for status, count in result.all():
            print(f"Status: {status}, Count: {count}")

if __name__ == "__main__":
    asyncio.run(test_song_status())
