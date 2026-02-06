import asyncio
import os
import sys

# Robust path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"DEBUG: Root path set to: {project_root}")

try:
    from core.database import AsyncSessionLocal
    from app.models.song import SongSource, Song
    from app.services.scan_service import ScanService
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import app modules: {e}")
    sys.exit(1)

from sqlalchemy import select

async def main():
    print("🚀 Starting Quality Refresh Task...")
    
    async with AsyncSessionLocal() as db:
        # Get all local sources
        stmt = select(SongSource).where(SongSource.source == 'local')
        result = await db.execute(stmt)
        sources = result.scalars().all()
        
        print(f"Found {len(sources)} local sources. Analyzing...")
        
        service = ScanService()
        updated_count = 0
        
        for source in sources:
            file_path = source.url
            if not os.path.exists(file_path):
                continue
                
            try:
                # Use mutagens to inspect
                from mutagen import File
                audio = File(file_path)
                if not audio:
                    continue
                
                # Re-run quality logic
                try:
                    new_quality = service._analyze_quality(audio)
                except:
                    new_quality = 'PQ'

                # Force FLAC check
                filename = os.path.basename(file_path).lower()
                if '.flac' in filename or '.wav' in filename or '.alac' in filename:
                    if new_quality == 'PQ':
                         new_quality = 'SQ'

                # Update JSON
                data = source.data_json or {}
                if isinstance(data, str):
                    try: 
                        data = json.loads(data)
                    except: 
                        data = {}
                        
                old_quality = data.get('quality')
                
                if old_quality != new_quality:
                    data['quality'] = new_quality
                    # Also update format if missing
                    if 'format' not in data:
                        data['format'] = filename.split('.')[-1].upper()
                        
                    source.data_json = data
                    # Flag modification
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(source, "data_json")
                    
                    print(f"✅ Fixed: {filename[:30]}... | {old_quality} -> {new_quality}")
                    updated_count += 1
            except Exception as e:
                print(f"❌ Error: {e}")

        if updated_count > 0:
            await db.commit()
            print(f"🎉 Successfully updated {updated_count} records.")
        else:
            print("✨ No updates needed. Data shows 0 changes.")

if __name__ == "__main__":
    asyncio.run(main())
