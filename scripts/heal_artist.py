import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.artist import Artist
from app.services.metadata_healer import MetadataHealer
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def heal_specific_artist(artist_id):
    async with AsyncSessionLocal() as db:
        stmt = select(Artist).options(selectinload(Artist.sources)).where(Artist.id == artist_id)
        res = await db.execute(stmt)
        artist = res.scalar_one_or_none()
        
        if not artist:
            print(f"❌ Artist ID {artist_id} not found.")
            return
            
        print(f"🚑 Healing artist: {artist.name} (Current Avatar: {artist.avatar})")
        healer = MetadataHealer()
        success = await healer.heal_artist(db, artist)
        
        if success:
            print(f"✅ Success! New Avatar: {artist.avatar}")
        else:
            print("❌ Healing failed or not needed.")

if __name__ == "__main__":
    aid = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    asyncio.run(heal_specific_artist(aid))
