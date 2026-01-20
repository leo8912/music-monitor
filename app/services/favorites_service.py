import os
import shutil
import logging
from sqlalchemy.orm import Session
from core.config import config
from core.database import MediaRecord
from core.audio_downloader import AudioDownloader, AUDIO_CACHE_DIR

logger = logging.getLogger(__name__)

class FavoritesService:
    @staticmethod
    def get_favorites_dir():
        return config.get('storage', {}).get('favorites_dir', 'favorites')

    @staticmethod
    async def toggle_favorite(db: Session, unique_key: str, force_state: bool = None) -> dict:
        """
        Toggle favorite state for a media record.
        If force_state is provided, set to that state.
        """
        record = db.query(MediaRecord).filter_by(unique_key=unique_key).first()
        if not record:
            return {"success": False, "message": "Record not found"}

        # Determine new state
        new_state = not record.is_favorite if force_state is None else force_state
        
        if new_state == record.is_favorite:
             return {"success": True, "state": new_state, "message": "State unchanged"}

        favorites_dir = FavoritesService.get_favorites_dir()
        if not os.path.exists(favorites_dir):
            os.makedirs(favorites_dir)

        if new_state:
            # === Adding to Favorites ===
            
            # 1. Ensure audio is downloaded
            if not record.local_audio_path or not os.path.exists(os.path.join(AUDIO_CACHE_DIR, record.local_audio_path)):
                # Trigger download (basic version)
                logger.info(f"Favorite: {record.title} not downloaded, fetching...")
                dl = AudioDownloader()
                res = await dl.download(
                    source=record.source,
                    song_id=record.media_id,
                    title=record.title,
                    artist=record.author,
                    album=record.album,
                    pic_url=record.cover
                )
                if res:
                    record.local_audio_path = res['local_path']
                    record.audio_quality = res['quality']
                else:
                    return {"success": False, "message": "Failed to download audio for favorite"}

            # 2. Copy to Favorites Directory
            src_path = os.path.join(AUDIO_CACHE_DIR, record.local_audio_path)
            dst_path = os.path.join(favorites_dir, record.local_audio_path)
            
            try:
                shutil.copy2(src_path, dst_path)
                logger.info(f"Copied to favorites: {dst_path}")
            except Exception as e:
                logger.error(f"Failed to copy file to favorites: {e}")
                return {"success": False, "message": f"File copy failed: {e}"}
                
            record.is_favorite = True
            
        else:
            # === Removing from Favorites ===
            # Decide: Do we delete the file from favorites dir?
            # Usually yes to keep clean.
            if record.local_audio_path:
                fav_path = os.path.join(favorites_dir, record.local_audio_path)
                if os.path.exists(fav_path):
                    try:
                        os.remove(fav_path)
                        logger.info(f"Removed from favorites: {fav_path}")
                    except Exception as e:
                        logger.warning(f"Failed to remove file from favorites: {e}")
            
            record.is_favorite = False

        db.commit()
        return {"success": True, "state": record.is_favorite}
