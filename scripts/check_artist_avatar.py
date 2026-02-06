import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.artist import Artist
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def check_artist_avatar(query):
    async with AsyncSessionLocal() as db:
        stmt = select(Artist).options(selectinload(Artist.sources)).where(Artist.name.like(f"%{query}%"))
        res = await db.execute(stmt)
        artists = res.scalars().all()
        
        for a in artists:
            print(f"\n👤 ARTIST: {a.name} (ID: {a.id})")
            print(f"   Avatar: {a.avatar}")
            print(f"   Is Avatar HTTP? {'YES 🚩' if a.avatar and a.avatar.startswith('http') else 'NO'}")
            for src in a.sources:
                print(f"   - [{src.source}] Source Avatar: {src.avatar}")

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "宿羽阳"
    asyncio.run(check_artist_avatar(q))
