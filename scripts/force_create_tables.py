import asyncio
import sys
import logging

# Ensure project root is in path
sys.path.insert(0, "/app")

from core.database import engine
from app.models.base import Base
# Import all models to ensure they are registered in Base.metadata
from app.models.song import Song, SongSource
from app.models.artist import Artist
from app.models.system_settings import SystemSettings

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_repair")

async def force_create_tables():
    print("="*50)
    print("🛠️  Starting Missing Table Restoration")
    print("="*50)
    
    print(f"Target Database: {engine.url}")
    print("Checking for missing tables...")

    try:
        async with engine.begin() as conn:
            # create_all checks for existence automatically and only creates missing tables
            await conn.run_sync(Base.metadata.create_all)
        
        print("\n✅ Operation 'create_all' completed successfully.")
        print("   (This safely creates any tables that were missing: e.g., song_sources)")
        
    except Exception as e:
        print(f"\n❌ Failed to create tables: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(force_create_tables())
