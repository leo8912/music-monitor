import os
import time
import logging
from core.config import config
from core.audio_downloader import AUDIO_CACHE_DIR

logger = logging.getLogger(__name__)

from datetime import datetime, timedelta
from core.database import SessionLocal, MediaRecord

def cleanup_cache():
    """
    Cleanup cache based on song PUBLISH TIME.
    Songs older than 'storage.retention_days' (default 180) will be deleted.
    """
    days = config.get('storage', {}).get('retention_days', 180)
    if days <= 0:
        logger.info("Cache retention disabled (days=0).")
        return

    logger.info(f"Starting cache cleanup (Retention: {days} days from publish time)...")
    
    db = SessionLocal()
    try:
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Query records that have local files but are older than cutoff
        # Note: We rely on DB 'publish_time'. If missing, we skip? 
        # Or if missing assume old? Let's assume keep if missing to be safe.
        records_to_clean = db.query(MediaRecord).filter(
            MediaRecord.local_audio_path.isnot(None),
            MediaRecord.publish_time < cutoff_date
        ).all()
        
        count = 0
        size_freed = 0
        
        for r in records_to_clean:
            # Construct full path
            # Assuming basename is stored in local_audio_path
            # Ignore LIBRARY files
            if r.local_audio_path.startswith("LIBRARY/"):
                continue
                
            file_path = os.path.join(AUDIO_CACHE_DIR, os.path.basename(r.local_audio_path))
            
            if os.path.exists(file_path):
                try:
                    size = os.path.getsize(file_path)
                    os.remove(file_path)
                    size_freed += size
                    logger.info(f"Deleted expired cache: {r.title} (Published: {r.publish_time})")
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")
            
            # Update DB
            r.local_audio_path = None
            r.audio_quality = None
            count += 1
            
        if count > 0:
            db.commit()
            logger.info(f"Cleanup complete. Deleted {count} files, freed {size_freed / 1024 / 1024:.2f} MB.")
        else:
            logger.info("Cleanup complete. No expired files found.")
            
    except Exception as e:
        logger.error(f"Cache cleanup error: {e}")
    finally:
        db.close()
