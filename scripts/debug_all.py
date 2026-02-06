import asyncio
import os
import sys
import json

# 添加项目根目录到路径
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from app.services.deduplication_service import DeduplicationService
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def debug_all_versions():
    print("🔍 Deep Inspection for '潮汐锁定'...")
    async with AsyncSessionLocal() as db:
        stmt = select(Song).options(
            selectinload(Song.artist),
            selectinload(Song.sources)
        ).where(Song.title.like("%潮汐锁定%"))
        
        result = await db.execute(stmt)
        songs = result.scalars().all()
        
        print(f"📊 Total Raw Songs Found: {len(songs)}")
        
        for s in songs:
            print(f"\n--- [Song ID: {s.id}] ---")
            print(f"Title: {s.title}")
            print(f"Artist: {s.artist.name if s.artist else 'None'}")
            print(f"Cover (Song Table): {s.cover}")
            print(f"Local Path: {s.local_path}")
            print(f"Status: {s.status}")
            print(f"Sources:")
            for src in s.sources:
                print(f"  - Source: {src.source} | SourceID: {src.source_id} | Cover: {src.cover}")

        print("\n--- Running Deduplication Logic ---")
        dedup_results = DeduplicationService.deduplicate_songs(songs)
        print(f"📊 Items after Deduplication: {len(dedup_results)}")
        
        for res in dedup_results:
            print(f"\nResult Title: {res['title']}")
            print(f"Result Cover: {res['cover']}")
            print(f"Result Source: {res['source']}")
            print(f"Local Files count: {len(res['local_files'])}")

if __name__ == "__main__":
    asyncio.run(debug_all_versions())
