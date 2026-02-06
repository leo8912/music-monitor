
import asyncio
from sqlalchemy import select
from core.database import AsyncSessionLocal
from app.models.artist import Artist
from app.models.song import Song
from datetime import datetime

async def check_artist_songs(artist_id):
    async with AsyncSessionLocal() as db:
        stmt = select(Song).where(Song.artist_id == artist_id)
        result = await db.execute(stmt)
        songs = result.scalars().all()
        
        print(f"Checking {len(songs)} songs for artist {artist_id}")
        for s in songs:
            pt = s.publish_time
            if pt and not isinstance(pt, datetime):
                print(f"!!! TYPE MISMATCH: Song ID: {s.id}, Title: {s.title}, publish_time: {repr(pt)}, type: {type(pt)}")
            # Also check if it's a very old date or future date
            if isinstance(pt, datetime):
                if pt.year < 1900 or pt.year > 2030:
                     print(f"--- WEIRD DATE: Song ID: {s.id}, Title: {s.title}, publish_time: {pt}")

if __name__ == "__main__":
    asyncio.run(check_artist_songs(4))
