
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app.models.base import engine, AsyncSessionLocal
from app.models.song import Song
from app.services.library import LibraryService
from sqlalchemy import select

async def verify_real_download():
    async with AsyncSessionLocal() as db:
        service = LibraryService()
        
        # 1. Pick a song
        result = await db.execute(select(Song).limit(1))
        song = result.scalars().first()
        
        if not song:
            print("No songs in DB to test with.")
            return

        print(f"Testing redownload for Song: {song.title} (ID: {song.id})")
        
        # 2. Pick a reliable source for testing: Netease "稻香"
        source = "netease"
        track_id = "2651425710" 
        quality = 999 # Testing Lossless FLAC
        
        print(f"Target: {source}:{track_id} at Quality: {quality}")
        
        # 3. Trigger redownload with metadata overrides
        try:
            success = await service.redownload_song(
                db,
                song_id=song.id,
                source=source,
                source_id=track_id,
                quality=quality,
                title="稻香",
                artist="周杰伦"
            )
            
            if success:
                print("✅ Redownload call returned Success")
                # Refresh song from DB
                await db.refresh(song)
                print(f"New Path: {song.local_path}")
                print(f"Status: {song.status}")
                
                if song.local_path and os.path.exists(song.local_path):
                    size = os.path.getsize(song.local_path)
                    print(f"✅ File exists at {song.local_path}, Size: {size} bytes")
                else:
                    print("❌ File NOT found at path!")
            else:
                print("❌ Redownload call returned Failure")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"❌ Exception during redownload: {e}")

if __name__ == "__main__":
    asyncio.run(verify_real_download())
