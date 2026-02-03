import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import select
from sqlalchemy.orm import selectinload # Import selectinload
from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from app.services.music_providers.qqmusic_provider import QQMusicProvider
from app.services.music_providers.netease_provider import NeteaseProvider

async def check_metadata():
    print("--- 1. Checking Provider Metadata ---")
    qq = QQMusicProvider()
    
    # Test song from user screenshot
    keywords = ["十一一种孤独 (Live) 宿羽阳", "你说你不知该怎么和妈妈说 (Live) 宿羽阳"]
    
    for kw in keywords:
        print(f"\nSearching for: {kw}")
        try:
            # Search QQ
            results = await qq.search_song(kw) # Use search_song
            if results:
                top = results[0]
                print(f"  [QQ] Top Result: {top.title}")
                print(f"  [QQ] Album: {top.album}")
                print(f"  [QQ] Cover: {top.cover_url}")
                print(f"  [QQ] Song ID: {top.id}")
                
                if top.cover_url:
                    print(f"  [QQ] Has independent cover!")
                else:
                    print(f"  [QQ] Using default/album cover?")
            else:
                print("  [QQ] No results")
        except Exception as e:
            print(f"  [QQ] Error: {e}")

async def check_db_status():
    print("\n--- 2. Checking Local Database Status ---")
    
    async with AsyncSessionLocal() as db:
        stmt = select(Song).options(selectinload(Song.sources)).where(Song.artist.has(name="宿羽阳")) # Add eager load
        result = await db.execute(stmt)
        songs = result.scalars().all()
        
        print(f"Found {len(songs)} songs for 宿羽阳:")
        pending_count = 0
        for s in songs:
            if "十一一种" in s.title or "妈妈" in s.title:
                print(f"  Song: {s.title}")
                print(f"    Status: {s.status}")
                print(f"    Song Cover: {s.cover}")
                print(f"    Album: {s.album}")
                
                # Check sources
                for src in s.sources:
                     print(f"    - Source: {src.source} | Cover: {src.cover}")

            if s.status == 'PENDING':
                pending_count += 1
                
        print(f"\nTotal PENDING songs: {pending_count}/{len(songs)}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_metadata())
    asyncio.run(check_db_status())
