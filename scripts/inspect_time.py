import asyncio
import os
import sys

# Robust path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from core.database import AsyncSessionLocal
    from app.models.song import Song
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import app modules: {e}")
    sys.exit(1)

from sqlalchemy import select

async def main():
    print("🔍 Inspecting Song created_at precision...")
    
    async with AsyncSessionLocal() as db:
        # Get latest 10 songs
        stmt = select(Song).order_by(Song.id.desc()).limit(10)
        result = await db.execute(stmt)
        songs = result.scalars().all()
        
        print(f"{'ID':<5} | {'Title':<30} | {'Created At (Raw)':<30}")
        print("-" * 70)
        for s in songs:
            print(f"{s.id:<5} | {s.title[:28]:<30} | {str(s.created_at):<30}")

if __name__ == "__main__":
    asyncio.run(main())
