
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import delete
from core.database import AsyncSessionLocal
from app.models.song import Song

async def delete_id28():
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Song).where(Song.id == 28))
        await db.commit()
        print("Deleted ID 28")

if __name__ == "__main__":
    asyncio.run(delete_id28())
