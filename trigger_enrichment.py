
import asyncio
import logging
from app.services.enrichment_service import EnrichmentService
from core.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.song import Song

# Setup logging
logging.basicConfig(level=logging.INFO)

async def trigger():
    keyword = "我可以"
    print(f"Searching for song matching: {keyword}")
    
    async with AsyncSessionLocal() as db:
        stmt = select(Song).where(Song.title.ilike(f"%{keyword}%"))
        result = await db.execute(stmt)
        song = result.scalars().first()
        
        if song:
            print(f"Found song: {song.title} (ID: {song.id})")
            service = EnrichmentService()
            await service.enrich_song(song.id)
            print("Enrichment triggered.")
        else:
            print("Song not found.")

if __name__ == "__main__":
    asyncio.run(trigger())
