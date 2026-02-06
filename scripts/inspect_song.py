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

async def check_song_detail(title):
    async with AsyncSessionLocal() as db:
        stmt = select(Song).options(selectinload(Song.sources)).where(Song.title.like(f"%{title}%"))
        res = await db.execute(stmt)
        songs = res.scalars().all()
        
        if not songs:
            print(f"❌ Song matching '{title}' not found.")
            return

        for song in songs:
            print(f"\n========================================")
            print(f"🎵 SONG INFO (ID: {song.id})")
            print(f"========================================")
            print(f"Title: {song.title}")
            print(f"Artist ID: {song.artist_id}")
            print(f"Cover: {repr(song.cover)}")
            print(f"Local Path: {song.local_path}")
            print(f"Status: {song.status}")
            
            print(f"\n📡 SOURCES ({len(song.sources)}):")
            for src in song.sources:
                print(f"-- Source: {src.source} (ID: {src.source_id}) --")
                print(f"   Cover: {repr(src.cover)}")
                
                # Handle data_json which might be dict or string
                data = src.data_json
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except:
                        data = {}
                
                if isinstance(data, dict):
                    print(f"   Data JSON Cover: {repr(data.get('cover'))}")
                else:
                    print(f"   Data JSON: {repr(data)}")

if __name__ == "__main__":
    t = sys.argv[1] if len(sys.argv) > 1 else "潮汐锁定"
    asyncio.run(check_song_detail(t))
