
import asyncio
import os
import sys

sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import SongSource
from sqlalchemy import select
from mutagen import File as MutagenFile

async def fix_all_robust():
    async with AsyncSessionLocal() as db:
        print("Starting Robust Quality Fix...")
        stmt = select(SongSource).where(SongSource.source == 'local')
        result = await db.execute(stmt)
        sources = result.scalars().all()
        
        updated_count = 0
        
        for src in sources:
            if not src.url: continue
            
            # Determine extension
            ext = os.path.splitext(src.url)[1].lower()
            
            # 1. Determine Target "Minimum" Quality based on Extension
            min_quality = "PQ"
            if ext in ['.flac', '.wav', '.ape', '.alac', '.aiff']:
                min_quality = "SQ"
            elif ext in ['.mp3', '.m4a', '.aac']:
                min_quality = "PQ" # MP3 *can* be PQ
                
            # 2. Try to get Precise Quality from Mutagen
            precise_quality = None
            try:
                if os.path.exists(src.url):
                    audio = MutagenFile(src.url)
                    if audio and audio.info:
                        bits = getattr(audio.info, 'bits_per_sample', 0)
                        rate = getattr(audio.info, 'sample_rate', 0)
                        bitrate = getattr(audio.info, 'bitrate', 0)
                        
                        if bits > 16 or rate > 48000:
                            precise_quality = "HR"
                        elif ext in ['.flac', '.wav', '.ape', '.alac', '.aiff']:
                            precise_quality = "SQ"
                        elif bitrate >= 250000:
                            precise_quality = "HQ"
                        else:
                            precise_quality = "PQ"
            except Exception as e:
                # If mutagen fails, we rely on min_quality
                pass
                
            # 3. Decision Logic
            final_quality = precise_quality if precise_quality else min_quality
            
            # If Precise Quality is somehow WORSE than Min Quality (e.g. Broken header says 0 bits?), enforce Min
            priority = {"HR": 4, "SQ": 3, "HQ": 2, "PQ": 1}
            if priority.get(final_quality, 1) < priority.get(min_quality, 1):
                final_quality = min_quality
                
            # 4. Update DB if needed
            current_data = dict(src.data_json or {})
            current_q = current_data.get('quality', 'PQ')
            
            if current_q != final_quality:
                print(f"Updating {src.id} ({os.path.basename(src.url)}): {current_q} -> {final_quality}")
                current_data['quality'] = final_quality
                current_data['format'] = ext.replace('.', '').upper()
                current_data['quality_details'] = f"{current_data['format']} | {final_quality}"
                
                src.data_json = current_data
                updated_count += 1
                
        if updated_count > 0:
            await db.commit()
            print(f"Successfully updated {updated_count} files.")
        else:
            print("All files are already correct.")

if __name__ == "__main__":
    asyncio.run(fix_all_robust())
