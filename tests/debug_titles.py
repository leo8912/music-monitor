
import asyncio
import sys
import os
from sqlalchemy import select

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song

async def debug_titles():
    async with AsyncSessionLocal() as session:
        print("--- All Song Titles ---")
        stmt = select(Song.title).order_by(Song.title)
        titles = await session.execute(stmt)
        all_titles = titles.scalars().all()
        
        for t in all_titles:
            print(f"- {t}")

if __name__ == "__main__":
    asyncio.run(debug_titles())
