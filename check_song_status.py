import asyncio
from sqlalchemy import select
from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from sqlalchemy.orm import selectinload

async def check_song(title_keyword):
    async with AsyncSessionLocal() as db:
        stmt = select(Song).options(
            selectinload(Song.sources),
            selectinload(Song.artist)
        ).where(Song.title.ilike(f"%{title_keyword}%"))
        
        result = await db.execute(stmt)
        songs = result.scalars().all()
        
        if not songs:
            print(f"No songs found with title containing '{title_keyword}'")
            return

        for s in songs:
            print(f"--- Song: {s.title} (ID: {s.id}) ---")
            print(f"  Artist: {s.artist.name if s.artist else 'None'}")
            print(f"  Album: {s.album}")
            print(f"  Cover (DB): {s.cover}")
            print(f"  Publish Time: {s.publish_time}")
            print(f"  Status: {s.status}")
            
            print("  Sources:")
            for src in s.sources:
                print(f"    - Type: {src.source}")
                print(f"      ID: {src.source_id}")
                print(f"      URL: {src.url}")
                print(f"      Data JSON: {src.data_json}")
                print(f"      Source Cover: {src.cover}")

if __name__ == "__main__":
    asyncio.run(check_song("我可以"))
