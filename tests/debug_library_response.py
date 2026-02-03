
import asyncio
import os
import sys
import json
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import AsyncSessionLocal
from app.repositories.song import SongRepository
from app.services.deduplication_service import DeduplicationService
from app.models.song import Song

async def debug_response():
    async with AsyncSessionLocal() as db:
        print("🔍 Fetching songs from DB...")
        
        # Mimic LibraryRouter.get_library_songs logic
        stmt = select(Song).options(
            selectinload(Song.artist),
            selectinload(Song.sources)
        ).order_by(Song.id.desc()).limit(5)
        
        songs = (await db.execute(stmt)).scalars().all()
        print(f"📄 Fetched {len(songs)} songs.")
        
        # Deduplicate
        items = DeduplicationService.deduplicate_songs(songs)
        
        print("\n📊 Deduplicated Items (First 2):")
        for i, item in enumerate(items[:2]):
            print(f"\n--- Item {i+1} ---")
            print(f"Title: {item.get('title')}")
            print(f"Local Path (root): {item.get('local_path')}")
            print(f"Local Path (camel): {item.get('localPath')}") # check if casing issue
            print(f"Sources: {item.get('availableSources')}")
            print(f"Local Files: {json.dumps(item.get('localFiles'), indent=2, ensure_ascii=False)}")
            
            # Check raw sources
            raw_sources = item.get('source_id')
            print(f"Main Source ID: {raw_sources}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(debug_response())
