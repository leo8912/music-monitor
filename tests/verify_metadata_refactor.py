import asyncio
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from core.database import AsyncSessionLocal
from app.services.library import LibraryService

async def verify():
    print("--------------------------------------------------")
    print("Starting Metadata Refactor Verification")
    print("--------------------------------------------------")
    
    async with AsyncSessionLocal() as db:
        service = LibraryService()
        
        # Test 1: Local Enrich
        print("\n[Test 1] Testing enrich_local_files (limit=1)...")
        try:
            count = await service.enrich_local_files(db, limit=1)
            print(f"✅ enrich_local_files executed successfully.")
            print(f"   Processed count: {count}")
        except Exception as e:
            print(f"❌ enrich_local_files failed: {e}")
            import traceback
            traceback.print_exc()

        # Test 2: Library Refresh
        print("\n[Test 2] Testing refresh_library_metadata (limit=1)...")
        try:
            count = await service.refresh_library_metadata(db, limit=1)
            print(f"✅ refresh_library_metadata executed successfully.")
            print(f"   Processed count: {count}")
        except Exception as e:
            print(f"❌ refresh_library_metadata failed: {e}")
            import traceback
            traceback.print_exc()

    print("\n--------------------------------------------------")
    print("Verification Complete")
    print("--------------------------------------------------")

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(verify())
    except Exception as e:
        print(f"Loop execution failed: {e}")
