import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.artist import Artist
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def check_artists():
    async with AsyncSessionLocal() as db:
        stmt = select(Artist).options(selectinload(Artist.sources)).where(Artist.name.like("%宿羽阳%"))
        res = await db.execute(stmt)
        artists = res.scalars().all()
        
        print(f"📊 Found {len(artists)} artist(s) matching '宿羽阳':")
        for a in artists:
            print(f"  ID: {a.id} | Name: {a.name}")
            print(f"    Sources: {', '.join([s.source for s in a.sources])}")

if __name__ == "__main__":
    asyncio.run(check_artists())
