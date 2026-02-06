import asyncio
import os
import sys
import json

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def check_song_data(title_query):
    print(f"🔍 Searching for songs with title matching: '{title_query}'")
    async with AsyncSessionLocal() as db:
        stmt = select(Song).options(selectinload(Song.sources)).where(Song.title.like(f"%{title_query}%"))
        res = await db.execute(stmt)
        songs = res.scalars().all()
        
        if not songs:
            print("❌ No songs found.")
            return

        print(f"📊 Found {len(songs)} song(s).")
        for s in songs:
            print(f"\n[Song ID: {s.id}]")
            print(f"  Title: {s.title}")
            print(f"  Cover Field: {s.cover}")
            print(f"  Is HTTP? {'YES 🚩' if s.cover and s.cover.startswith('http') else 'NO'}")
            print(f"  Local Path: {s.local_path}")
            print(f"  Sources ({len(s.sources)}):")
            for src in s.sources:
                print(f"    - [{src.source}] Cover: {src.cover}")
                print(f"      Is Source HTTP? {'YES 🚩' if src.cover and src.cover.startswith('http') else 'NO'}")

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "潮汐锁定"
    asyncio.run(check_song_data(query))
