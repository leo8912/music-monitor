
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from core.database import AsyncSessionLocal
from app.models.song import Song
from app.models.artist import Artist

async def locate_guniang():
    async with AsyncSessionLocal() as db:
        stmt = select(Song).options(selectinload(Song.artist)).where(Song.title.like("%姑娘%"))
        result = await db.execute(stmt)
        songs = result.scalars().all()
        
        print(f"Found {len(songs)} songs matching '姑娘':")
        for s in songs:
            a_id = s.artist_id
            a_name = s.artist.name if s.artist else "NONE"
            print(f"  ID: {s.id}, Title: {s.title}, ArtistID: {a_id}, ArtistName: {a_name}, LocalPath: {s.local_path}")

if __name__ == "__main__":
    asyncio.run(locate_guniang())
