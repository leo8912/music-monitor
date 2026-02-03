
import asyncio
import os
import sys
import hashlib
from sqlalchemy import select, delete

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import AsyncSessionLocal, init_db
from app.models.artist import Artist
from app.models.song import Song, SongSource
from app.services.scan_service import ScanService

async def verify_duplicate_logic():
    async with AsyncSessionLocal() as db:
        print("🔧 Initializing Test Data...")
        
        # 1. Create a dummy Artist & Song
        artist = Artist(name="Test Artist")
        song = Song(title="Test Song", artist=artist)
        
        db.add(artist)
        db.add(song)
        await db.commit()
        await db.refresh(song)
        
        print(f"✅ Created Test Song: ID={song.id}")
        
        # Service instance
        service = ScanService()
        
        # 2. Insert First File (Path A)
        filename = "test_duplicate.mp3"
        path_a = "/data/music/custom/test_duplicate.mp3"
        
        print(f"📄 Inserting File A: {path_a}")
        await service._create_song_source(
            db=db,
            song_obj=song,
            filename=filename,
            file_path=path_a,
            data_json={"quality": "HQ"}
        )
        await db.commit()
        
        # 3. Insert Second File (Path B) - SAME filename, DIFFERENT path
        path_b = "/data/music/downloads/test_duplicate.mp3"
        print(f"📄 Inserting File B: {path_b}")
        await service._create_song_source(
            db=db,
            song_obj=song,
            filename=filename,
            file_path=path_b,
            data_json={"quality": "SQ"}
        )
        await db.commit()
        
        # 4. Input Third File (Path A again) - Should detect existing
        print(f"📄 Inserting File A again (Should be idempotent)...")
        await service._create_song_source(
            db=db,
            song_obj=song,
            filename=filename,
            file_path=path_a,
            data_json={"quality": "HQ_UPDATED"}
        )
        await db.commit()

        # 5. Verify Results
        stmt = select(SongSource).where(SongSource.song_id == song.id)
        sources = (await db.execute(stmt)).scalars().all()
        
        print("\n📊 Verification Results:")
        print(f"Total Sources Found: {len(sources)} (Expected: 2)")
        
        path_a_found = False
        path_b_found = False
        
        for s in sources:
            print(f" - Source ID: {s.source_id}, Path: {s.url}, Quality: {s.data_json.get('quality')}")
            
            if s.url == path_a:
                path_a_found = True
                if s.data_json.get('quality') == "HQ_UPDATED":
                    print("   ✅ Path A updated correctly")
                else:
                    print("   ❌ Path A content NOT updated")
                    
            if s.url == path_b:
                path_b_found = True
                expected_hash = hashlib.md5(path_b.encode('utf-8')).hexdigest()[:6]
                expected_id = f"{filename}_{expected_hash}"
                if s.source_id == expected_id:
                    print("   ✅ Path B has correct Hash ID")
                else:
                    print(f"   ❌ Path B ID incorrect. Got: {s.source_id}, Expected: {expected_id}")

        if len(sources) == 2 and path_a_found and path_b_found:
            print("\n🎉 TEST PASSED: Logic handles duplicates correctly!")
        else:
            print("\n💥 TEST FAILED: Logic incorrect.")
            
        # Cleanup
        print("\n🧹 Cleaning up...")
        await db.delete(song)
        await db.delete(artist)
        # Cascade should delete sources, but let's be safe
        # (Actually cascade is configured in models usually)
        await db.commit()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify_duplicate_logic())
