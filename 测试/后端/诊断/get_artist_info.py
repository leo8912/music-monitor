import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.artist import Artist, ArtistSource
from sqlalchemy import select

async def run():
    async with AsyncSessionLocal() as db:
        stmt = select(Artist).where(Artist.name == '宿羽阳')
        artist = (await db.execute(stmt)).scalar_one_or_none()
        if not artist:
            print("Artist '宿羽阳' not found.")
            return
            
        print(f"Artist Found: {artist.name} (ID: {artist.id})")
        
        src_stmt = select(ArtistSource).where(ArtistSource.artist_id == artist.id)
        sources = (await db.execute(src_stmt)).scalars().all()
        ids = {s.source: s.source_id for s in sources}
        print(f"Sources: {ids}")

if __name__ == "__main__":
    asyncio.run(run())
