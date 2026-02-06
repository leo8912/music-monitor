import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def inspect_specific_song():
    print(f"🔍 Inspecting '一生所爱'...")
    
    async with AsyncSessionLocal() as db:
        # Check Song Table
        stmt = select(Song).options(
            selectinload(Song.sources),
            selectinload(Song.artist)
        ).where(Song.title == "一生所爱")
        
        result = await db.execute(stmt)
        songs = result.scalars().all()
        print(f"📊 Found {len(songs)} song records.")

        if not songs:
            return

        s = songs[1] if len(songs) > 1 else songs[0]
        
        print(f"\n========================================", flush=True)
        print(f"🎵 SONG: {s.title} (ID: {s.id})", flush=True)
        print(f"========================================", flush=True)
        print(f"Title: {s.title}", flush=True)
        print(f"Artist: {s.artist.name if s.artist else 'Unknown'}", flush=True)
        print(f"DB Cover Field: {s.cover}", flush=True)
        print(f"DB Local Path: '{s.local_path}' (Is None: {s.local_path is None})", flush=True)
        print(f"DB Status: {s.status}", flush=True)
        
        # Check Sources
        for src in s.sources:
            print(f"\n-- Source: {src.source} --", flush=True)
            print(f"   URL: {src.url}", flush=True)
            print(f"   Source Cover: {getattr(src, 'cover', 'N/A')}", flush=True)
            print(f"   Data JSON Cover: {src.data_json.get('cover') if src.data_json else 'None'}", flush=True)

        file_path = s.local_path or f"audio_cache/{s.title}.flac" 
        
        # Check physical file tags
        print(f"\n========================================")
        print(f"💾 PHYSICAL FILE CHECK")
        print(f"========================================")
        abs_path = os.path.abspath(file_path)
        
        # Try finding the song object again to get the real path if the default one doesn't exist
        real_path = abs_path
        if not os.path.exists(abs_path) and s.local_path:
            if os.path.exists(s.local_path):
                real_path = s.local_path
                print(f"Using path from DB: {real_path}")

        if os.path.exists(real_path):
            print(f"File Exists: YES at {real_path}")
            try:
                import mutagen
                from mutagen.flac import FLAC
                from mutagen.id3 import ID3
                from mutagen.mp3 import MP3
                
                audio = mutagen.File(real_path)
                has_pic = False
                title = "N/A"
                artist = "N/A"
                
                if isinstance(audio, FLAC):
                    if audio.pictures: has_pic = True
                    title = audio.get("title", ["N/A"])[0]
                    artist = audio.get("artist", ["N/A"])[0]
                elif isinstance(audio, MP3) or isinstance(audio, ID3):
                    # ID3 often wrapped
                    if audio.tags:
                        if 'APIC:' in audio.tags or any(k.startswith('APIC') for k in audio.tags.keys()):
                            has_pic = True
                        title = str(audio.tags.get("TIT2", "N/A"))
                        artist = str(audio.tags.get("TPE1", "N/A"))
                
                print(f"Has Embedded Picture: {has_pic}")
                print(f"Title in Tag: {title}")
                print(f"Artist in Tag: {artist}")
            except Exception as e:
                print(f"Error reading tags: {e}")
        else:
            print(f"File Exists: NO (Searched: {real_path})")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(inspect_specific_song())
