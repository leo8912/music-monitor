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
            print(f"  Artist ID: {s.artist_id}")
            print(f"  Cover (Main): {s.cover}")
            print(f"  Local Path: {s.local_path}")
            print(f"  Status: {s.status}")
            print(f"  Sources ({len(s.sources)}):")
            for src in s.sources:
                print(f"    - Source: {src.source}")
                print(f"      Source ID: {src.source_id}")
                print(f"      Cover: {src.cover}")
                
                # Check data_json if it exists
                if hasattr(src, 'data_json') and src.data_json:
                    data = src.data_json
                    if isinstance(data, str):
                        try:
                            data = json.loads(data)
                        except:
                            pass
                    if isinstance(data, dict):
                        print(f"      Data JSON Cover: {data.get('cover')}")

if __name__ == "__main__":
    # Check for "潮汐锁定" as a baseline, or any other song the user might be looking at
    query = sys.argv[1] if len(sys.argv) > 1 else "潮汐锁定"
    asyncio.run(check_song_data(query))
