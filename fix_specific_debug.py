
import asyncio
import os
import sys

sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from mutagen import File as MutagenFile

async def fix_specific():
    async with AsyncSessionLocal() as db:
        print("Searching for '一生所爱' local source...")
        
        # Join Song to find by title, then get sources
        stmt = select(SongSource).join(SongSource.song).where(
            Song.title.like("%一生所爱%"), 
            SongSource.source == 'local'
        )
        result = await db.execute(stmt)
        sources = result.scalars().all()
        
        if not sources:
            print("No local source found for '一生所爱'!")
            return

        for src in sources:
            print(f"Checking Source ID: {src.id}")
            print(f"URL: {src.url}")
            
            if not os.path.exists(src.url):
                print("File NOT found on disk.")
                continue
                
            ext = os.path.splitext(src.url)[1].lower()
            print(f"Extension detected: '{ext}'")
            
            quality = "PQ"
            if ext in ['.flac', '.wav', '.ape', '.alac', '.aiff']:
                print("Extension matches SQ list.")
                quality = "SQ"
            else:
                print("Extension does NOT match SQ list.")
                
            current_data = src.data_json or {}
            print(f"Current Data: {current_data}")
            
            # Force update even if same
            print(f"Forcing update to: {quality}")
            current_data['quality'] = quality
            current_data['format'] = ext.replace('.', '').upper()
            src.data_json = dict(current_data)
            
            db.add(src) # Mark as modified
            
        await db.commit()
        print("Commit complete.")

if __name__ == "__main__":
    asyncio.run(fix_specific())
