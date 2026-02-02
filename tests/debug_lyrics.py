import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song
from sqlalchemy import select
from app.services.metadata_service import MetadataService
import mutagen
from mutagen.id3 import ID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4

async def debug_lyrics():
    print("=== Lyric Extraction Debug Tool ===")
    
    async with AsyncSessionLocal() as db:
        # Get a few songs with local paths
        stmt = select(Song).where(Song.local_path != None).limit(5)
        result = await db.execute(stmt)
        songs = result.scalars().all()
        
        if not songs:
            print("No local songs found in database.")
            return

        service = MetadataService()

        for song in songs:
            print(f"\n--- Checking Song: {song.title} ({song.id}) ---")
            print(f"Local Path: {song.local_path}")
            
            # Check file existence
            if not os.path.exists(song.local_path):
                print(f"❌ File not found: {song.local_path}")
                continue
            
            print(f"✅ File exists.")
            
            # 1. Inspect Mutagen Tags
            try:
                audio = mutagen.File(song.local_path)
                if audio:
                    print(f"Type: {type(audio)}")
                    print("Tags keys:", audio.tags.keys() if audio.tags else "No Tags")
                    
                    # Print raw lyrics frames if found
                    if isinstance(audio.tags, ID3):
                        for key in audio.tags.keys():
                            if 'USLT' in key or 'SYLT' in key:
                                print(f"Found Lyric Frame {key}: {audio.tags[key].text[:50]}...")
                    elif isinstance(audio, FLAC):
                        if 'LYRICS' in audio:
                            print(f"Found FLAC LYRICS: {audio['LYRICS'][0][:50]}...")
                else:
                    print("Mutagen could not parse file.")
            except Exception as e:
                print(f"Error inspecting tags: {e}")

            # 2. Test MetadataService Extraction
            extracted = await service._read_embedded_lyrics(song.local_path)
            if extracted:
                print(f"✅ MetadataService extracted: {len(extracted)} chars")
                print(f"Content preview: {extracted[:100]}...")
            else:
                print("❌ MetadataService failed to extract lyrics.")

if __name__ == "__main__":
    asyncio.run(debug_lyrics())
