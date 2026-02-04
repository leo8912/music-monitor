import asyncio
import os
import sys
import logging
import traceback

# [Fix] Add project root to sys.path to allow imports from 'core' and 'app'
sys.path.insert(0, "/app")

from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Setup logging to force stdout
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("diagnose_500")

# Mock Environment if needed
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:////config/music_monitor.db"

async def main():
    print("="*50)
    print("🔍 Starting Diagnostic for 500 Error")
    print("="*50)

    # 1. Check Database File
    db_path = "/config/music_monitor.db"
    print(f"Checking DB file at: {db_path}")
    if os.path.exists(db_path):
        print(f"✅ DB file exists. Size: {os.path.getsize(db_path)} bytes")
    else:
        print("❌ DB file NOT found!")
        return

    # 2. Test Connection
    try:
        from core.database import DATABASE_URL
        print(f"Connecting to: {DATABASE_URL}")
        engine = create_async_engine(DATABASE_URL, echo=False)
        async with engine.connect() as conn:
            print("✅ Database connection successful")
            
            # 3. Inspect Schema
            print("\n📋 Inspecting 'songs' table schema...")
            # We need sync engine for inspection usually, or run raw sql
            columns = await conn.execute(text("PRAGMA table_info(songs)"))
            cols = [row[1] for row in columns.fetchall()]
            print(f"Current Columns in DB: {cols}")
            
            required_cols = ['id', 'title', 'artist_id', 'album', 'local_path', 'status', 'publish_time', 'created_at']
            missing = [c for c in required_cols if c not in cols]
            if missing:
                print(f"❌ MISSING COLUMNS: {missing}")
            else:
                print("✅ Core columns present")

    except Exception as e:
        print(f"❌ Database Connectivity Error: {e}")
        traceback.print_exc()
        return

    # 4. Test Model Loading & Query
    print("\n🔮 Testing SQLAlchemy Model Query...")
    try:
        # Manually import to trigger model registry
        from app.models.song import Song
        from app.models.artist import Artist
        
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            # Try simple select
            stmt = text("SELECT count(*) FROM songs")
            res = await session.execute(stmt)
            count = res.scalar()
            print(f"✅ 'songs' table row count: {count}")
            
            # Try ORM Select (This is what usually fails if schema mismatch)
            from sqlalchemy import select
            stmt = select(Song).limit(1)
            try:
                res = await session.execute(stmt)
                song = res.scalars().first()
                print(f"✅ ORM Query Successful. First song: {song.title if song else 'None'}")
            except Exception as e:
                print(f"❌ ORM Query FAILED: {e}")
                traceback.print_exc()

    except ImportError as e:
        print(f"❌ Import Error: {e}")
        return
    except Exception as e:
        print(f"❌ Model Interaction Error: {e}")
        traceback.print_exc()

    # 5. Test ScanService Logic
    print("\n🚀 Testing ScanService Logic...")
    try:
        from app.services.scan_service import ScanService
        service = ScanService()
        print(f"ScanService initialized. Paths: {service.scan_directories}")
        
        async with async_session() as session:
            print("Running _prune_missing_files...")
            await service._prune_missing_files(session)
            print("✅ _prune_missing_files passed")
            
            # Start full scan mock (just directory listing)
            for dir_name in service.scan_directories:
                exists = os.path.exists(dir_name)
                print(f"Checking dir {dir_name}: {'Exists' if exists else 'MISSING'}")
                if exists:
                    try:
                        files = os.listdir(dir_name)
                        print(f"  - Found {len(files)} files")
                    except Exception as e:
                        print(f"  ❌ Read Error: {e}")

    except Exception as e:
        print(f"❌ ScanService Failed: {e}")
        traceback.print_exc()

    print("\nDONE.")

if __name__ == "__main__":
    asyncio.run(main())
