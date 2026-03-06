import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime

async def check_healing_candidates():
    async with AsyncSessionLocal() as db:
        # Get songs with local_path
        stmt = select(Song).options(
            selectinload(Song.sources),
            selectinload(Song.artist)
        ).where(Song.local_path.isnot(None))
        
        songs = (await db.execute(stmt)).scalars().all()
        
        print(f"Total songs with local path: {len(songs)}")
        print("-" * 50)
        
        healer_needed = 0
        for song in songs:
            has_title = bool(song.title and song.title.strip())
            has_artist = bool(song.artist and song.artist.name)
            has_album = bool(song.album and song.album.strip())
            has_cover = bool(song.cover and (song.cover.startswith("/uploads/") or song.cover.startswith("uploads/")))
            has_publish_time = bool(song.publish_time)
            
            has_lyrics = False
            for src in song.sources:
                data = src.data_json if isinstance(src.data_json, dict) else {}
                if data.get("lyrics"):
                    has_lyrics = True
                    break
            
            is_complete = all([has_title, has_artist, has_album, has_cover, has_publish_time, has_lyrics])
            
            if not is_complete:
                healer_needed += 1
                missing = []
                if not has_title: missing.append("title")
                if not has_artist: missing.append("artist")
                if not has_album: missing.append("album")
                if not has_cover: missing.append(f"cover({song.cover})")
                if not has_publish_time: missing.append("publish_time")
                if not has_lyrics: missing.append("lyrics")
                
                print(f"❌ [{song.id}] {song.title} - {song.artist.name if song.artist else 'Unknown'}")
                print(f"   Missing: {', '.join(missing)}")
                print(f"   Last Enrich: {song.last_enrich_at}")
        
        print("-" * 50)
        print(f"Total healing candidates: {healer_needed}")

if __name__ == "__main__":
    asyncio.run(check_healing_candidates())
