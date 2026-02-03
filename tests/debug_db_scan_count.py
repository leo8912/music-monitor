
import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from sqlalchemy import select, func

async def inspect_db():
    async with AsyncSessionLocal() as session:
        # Count total songs
        result_songs = await session.execute(select(func.count(Song.id)))
        total_songs = result_songs.scalar()
        
        # Count total sources
        result_sources = await session.execute(select(func.count(SongSource.id)))
        total_sources = result_sources.scalar()
        
        # Count local sources specifically
        result_local = await session.execute(select(func.count(SongSource.id)).where(SongSource.source == 'local'))
        total_local_sources = result_local.scalar()

        print(f"\n📊 Database Statistics:")
        print(f"Total Songs (Unique Entries): {total_songs}")
        print(f"Total Sources (All Types): {total_sources}")
        print(f"Local File Sources: {total_local_sources}")
        
        # Find songs with multiple local sources
        print(f"\n🔍 Songs with Multiple Local Sources (Duplicates?):")
        
        # This query groups by song_id and counts local sources
        stmt = (
            select(Song.title, Song.artist_id, func.count(SongSource.id).label('count'))
            .join(SongSource, Song.id == SongSource.song_id)
            .where(SongSource.source == 'local')
            .group_by(Song.id, Song.title, Song.artist_id)
            .having(func.count(SongSource.id) > 1)
        )
        
        duplicates = await session.execute(stmt)
        dup_list = duplicates.all()
        
        if not dup_list:
            print("  None found.")
        else:
            for title, artist_id, count in dup_list:
                print(f"  - '{title}' (Artist ID: {artist_id}): {count} local files")

        # List all local files to see what's actually in DB
        print(f"\n📂 All Local Files in DB:")
        stmt_files = select(Song.title, SongSource.source_id).join(SongSource, Song.id == SongSource.song_id).where(SongSource.source == 'local')
        files = await session.execute(stmt_files)
        for title, filename in files.all():
            print(f"  - [{title}] {filename}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(inspect_db())
