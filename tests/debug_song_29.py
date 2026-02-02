import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song
from sqlalchemy import select
from app.services.metadata_service import MetadataService

async def debug_song_29():
    print("=== Debugging Song 29 ===")
    
    async with AsyncSessionLocal() as db:
        try:
            stmt = select(Song).where(Song.id == 29)
            result = await db.execute(stmt)
            song = result.scalars().first()
            
            if not song:
                print("❌ Song 29 not found in database.")
                return

            # Access attributes while session is open to avoid detach issues
            title = song.title
            artist = song.artist
            local_path = song.local_path
            
            print(f"Info: {title} - {artist}")
            print(f"Local Path: {local_path}")
            
            if not local_path:
                 print("❌ Local path is None.")
                 return

            if not os.path.exists(local_path):
                 print(f"❌ File does not exist at: {local_path}")
                 return
                 
            service = MetadataService()
            
            # Test 1: Read Embedded
            print("\n--- Testing Embedded Read ---")
            embedded = await service._read_embedded_lyrics(local_path)
            if embedded:
                print(f"✅ Found Embedded Lyrics ({len(embedded)} chars)")
            else:
                print("❌ No Embedded Lyrics Found.")
                
            # Test 2: Fallback
            print("\n--- Testing Online Fallback ---")
            # Create a dummy song object or just pass title/artist if service accepts it
            # MetadataService.fetch_lyrics(title, artist, [local_path])
            
            # We call fetch_lyrics with local_path to trigger the full logic including auto-embed
            final_lyrics = await service.fetch_lyrics(title, artist, local_path)
            
            if final_lyrics:
                 print(f"✅ Final Result: ({len(final_lyrics)} chars)")
            else:
                 print("❌ Final Result: None")

        except Exception as e:
            print(f"Error in DB or Service: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(debug_song_29())
