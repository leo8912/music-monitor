import asyncio
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.getcwd())

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from core.database import DATABASE_URL

async def inspect_db():
    print(f"🔍 Inspecting Database at: {DATABASE_URL}")
    
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.connect() as conn:
        print("\n📋 Checking existing tables...")
        # SQLite specific query for tables
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = result.scalars().all()
        
        if not tables:
            print("❌ No tables found! The database appears to be empty.")
        else:
            print(f"✅ Found {len(tables)} tables:")
            for t in tables:
                print(f"  - {t}")
                
        # Check specific critical tables
        critial_tables = ['system_settings', 'songs', 'song_sources', 'alembic_version']
        missing = [t for t in critial_tables if t not in tables]
        
        if missing:
            print(f"\n⚠️ User Warning: The following critical tables are MISSING: {missing}")
        else:
            print("\n✅ All critical tables appear to be present.")

    await engine.dispose()

if __name__ == "__main__":
    try:
        asyncio.run(inspect_db())
    except Exception as e:
        print(f"❌ Error during inspection: {e}")
