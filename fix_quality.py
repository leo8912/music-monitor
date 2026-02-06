
import asyncio
import os
import sys

sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from mutagen import File as MutagenFile

async def analyze_quality(file_path):
    try:
        audio = MutagenFile(file_path)
        if not audio: return "PQ"
        
        info = audio.info
        sample_rate = getattr(info, 'sample_rate', 0)
        bits = getattr(info, 'bits_per_sample', 0)
        bitrate = getattr(info, 'bitrate', 0)
        
        # HR Check
        if bits > 16 or sample_rate > 48000:
            return "HR"
            
        # SQ Check
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.flac', '.wav', '.ape', '.alac', '.aiff']:
            return "SQ"
            
        # HQ Check
        if bitrate >= 250000:
            return "HQ"
            
        return "PQ"
    except:
        return "PQ"

async def fix():
    async with AsyncSessionLocal() as db:
        print("Starting Quality Fix...")
        stmt = select(SongSource).where(SongSource.source == 'local')
        result = await db.execute(stmt)
        sources = result.scalars().all()
        
        updated = 0
        for src in sources:
            if not src.url or not os.path.exists(src.url):
                print(f"Skipping missing file: {src.url}")
                continue
                
            current_q = (src.data_json or {}).get('quality', 'PQ')
            new_q = await analyze_quality(src.url)
            
            if new_q != current_q:
                print(f"Updating {src.id}: {current_q} -> {new_q} ({src.url})")
                
                data = dict(src.data_json or {})
                data['quality'] = new_q
                
                # Also ensure format is set
                ext = os.path.splitext(src.url)[1].replace('.', '').upper()
                data['format'] = ext
                
                # Generate detail string if missing
                if 'quality_details' not in data:
                     data['quality_details'] = f"{ext} | {new_q}"

                src.data_json = data
                updated += 1
        
        if updated > 0:
            await db.commit()
            print(f"Successfully updated {updated} files.")
        else:
            print("No sources needed updates.")

if __name__ == "__main__":
    asyncio.run(fix())
