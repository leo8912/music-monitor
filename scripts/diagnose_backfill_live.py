
import asyncio
import logging
import os
import sys
import yaml

# Ensure imports
sys.path.append(os.getcwd())
from core.database import SessionLocal, MediaRecord
from core.audio_downloader import audio_downloader
from datetime import datetime, timedelta

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("diagnose_backfill")

from core.config import CONFIG_FILE_PATH

def load_config():
    with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

async def diagnose():
    print("--- Diagnosing Backfill Logic ---")
    
    config = load_config()
    db = SessionLocal()
    
    one_year_ago = datetime.now() - timedelta(days=365)
    
    # 1. Fetch Candidates
    records = db.query(MediaRecord).filter(
        MediaRecord.local_audio_path == None,
        MediaRecord.publish_time >= one_year_ago,
        MediaRecord.source.in_(['netease', 'qqmusic'])
    ).order_by(MediaRecord.publish_time.desc()).all()
    
    print(f"Total candidates in DB (last 1 year): {len(records)}")
    
    if not records:
        print("No records found in DB.")
        return

    # 2. Filter Logic
    netease_users = [u['name'] for u in config['monitor']['netease']['users']]
    qqmusic_users = [u['name'] for u in config['monitor']['qqmusic']['users']]
    
    print(f"Configured Netease Artists: {netease_users}")
    print(f"Configured QQMusic Artists: {qqmusic_users}")
    
    active_records = []
    skipped_records = []
    
    for r in records:
        match = False
        if r.source == 'netease':
            if r.author in netease_users:
                match = True
        elif r.source == 'qqmusic':
            if r.author in qqmusic_users:
                match = True
        
        if match:
            active_records.append(r)
        else:
            skipped_records.append(r)
            
    print(f"\nFiltered Results:")
    print(f"  Start Backfill (Matches): {len(active_records)}")
    print(f"  Skipped (No Match): {len(skipped_records)}")
    
    if skipped_records:
        print("\n[Sample Skipped Records]")
        for r in skipped_records[:5]:
            print(f"  - {r.title} | Author: '{r.author}' | Source: {r.source}")
            
    if active_records:
        print("\n[Sample Active Records]")
        for r in active_records[:5]:
            print(f"  - {r.title} | Author: '{r.author}' | Source: {r.source}")
            
        print("\n--- Testing Download for Top 3 Active Records ---")
        for r in active_records[:3]:
            print(f"\nProcessing: {r.title} - {r.author}")
            try:
                # Use current logic
                result = await audio_downloader.download(
                    source=r.source,
                    song_id=r.media_id,
                    title=r.title or "Unknown",
                    artist=r.author or "Unknown",
                    album=r.album or "",
                    pic_url=r.cover or ""
                )
                if result:
                    print(f"  ✅ Success: {result['local_path']} ({result['quality']}k)")
                else:
                    print(f"  ❌ Failed")
            except Exception as e:
                print(f"  ❌ Error: {e}")
                
    db.close()

if __name__ == "__main__":
    asyncio.run(diagnose())
