import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.artist import Artist
from sqlalchemy import select, func

async def count_online_avatars():
    async with AsyncSessionLocal() as db:
        stmt = select(func.count()).select_from(Artist).where(Artist.avatar.like("http%"))
        res = await db.execute(stmt)
        count = res.scalar()
        print(f"📊 Artists with online avatars: {count}")

if __name__ == "__main__":
    asyncio.run(count_online_avatars())
