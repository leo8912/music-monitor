
import asyncio
from sqlalchemy import select
from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from sqlalchemy.orm import selectinload

async def check_song(title_keyword):
    async with AsyncSessionLocal() as db:
        # Properly load relationships including artist
        stmt = select(Song).options(
            selectinload(Song.sources),
            selectinload(Song.artist)
        ).where(Song.title.ilike(f"%{title_keyword}%"))
        
        result = await db.execute(stmt)
        songs = result.scalars().all()
        
        print(f"Found {len(songs)} songs matching '{title_keyword}'")
        
        for s in songs:
            print(f"--- Song: {s.title} (ID: {s.id}) ---")
            # Safe access to artist name
            artist_name = s.artist.name if s.artist else "Unknown"
            print(f"Artist: {artist_name}")
            print(f"Cover (Song Table): {repr(s.cover)}")
            print(f"Local Path: {s.local_path}")
            
            for src in s.sources:
                print(f"  Source Type: {repr(src.source)}")
                print(f"  Source ID: {repr(src.source_id)}") # Check for exact string
                print(f"  Url: {repr(src.url)}")
                print(f"  Source Cover: {repr(src.cover)}")
                dj = src.data_json
                if dj and isinstance(dj, dict):
                     print(f"  Data JSON Cover: {repr(dj.get('cover'))}")
                # Handle potentially stringified JSON or dict
                dj_cover = "N/A"
                if isinstance(dj, dict):
                    dj_cover = dj.get('cover')
                elif isinstance(dj, str):
                    import json
                    try:
                        loaded = json.loads(dj)
                        dj_cover = loaded.get('cover')
                    except:
                        pass
                print(f"  Data JSON Cover: {dj_cover}")

if __name__ == "__main__":
    asyncio.run(check_song("行走的鱼"))
