import json
import asyncio
from sqlalchemy import select
from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from sqlalchemy.orm import selectinload
import os

async def inspect_song_sources(title_keyword):
    async with AsyncSessionLocal() as db:
        stmt = select(Song).options(
            selectinload(Song.sources)
        ).where(Song.title.ilike(f"%{title_keyword}%"))
        
        result = await db.execute(stmt)
        songs = result.scalars().all()
        
        print(f"Found {len(songs)} songs matching '{title_keyword}'")
        
        for s in songs:
            print(f"Song ID: {s.id} | Title: {s.title}")
            for src in s.sources:
                print(f"  -- Source ID: {src.source_id}")
                print(f"     Source Type: {src.source}")
                print(f"     URL: {src.url}")
                print(f"     File Exists: {os.path.exists(src.url) if src.url else 'No URL'}")
                
                dj = src.data_json
                if isinstance(dj, str):
                    try:
                        dj = json.loads(dj)
                    except:
                        pass
                
                print(f"     Data Quality: {dj.get('quality') if isinstance(dj, dict) else 'N/A'}")
                print(f"     Data Cover: {dj.get('cover') if isinstance(dj, dict) else 'N/A'}")

if __name__ == "__main__":
    asyncio.run(inspect_song_sources("我可以"))
