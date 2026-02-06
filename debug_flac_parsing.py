
import os
from mutagen import File as MutagenFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.song import Song
from core.database import SessionLocal
import asyncio

# Need async context for DB to find the path first
from core.database import AsyncSessionLocal

async def get_path():
    async with AsyncSessionLocal() as db:
        stmt = select(Song).options(selectinload(Song.sources)).where(Song.title.like("%一生所爱%"))
        result = await db.execute(stmt)
        song = result.scalars().first()
        if song and song.local_path:
            return song.local_path
    return None

def test_parsing():
    path = asyncio.run(get_path())
    print(f"Testing path: {path}")
    
    if not path:
        print("Song not found.")
        return

    if not os.path.exists(path):
        print("File does NOT exist on disk!")
        return
        
    print("File exists.")
    
    try:
        audio = MutagenFile(path)
        if audio:
            print(f"Mutagen Type: {type(audio)}")
            info = audio.info
            print(f"Sample Rate: {getattr(info, 'sample_rate', 'N/A')}")
            print(f"Bits: {getattr(info, 'bits_per_sample', 'N/A')}") 
            print(f"Bitrate: {getattr(info, 'bitrate', 'N/A')}")
        else:
            print("Mutagen returned None.")
    except Exception as e:
        print(f"Mutagen Error: {e}")

if __name__ == "__main__":
    test_parsing()
