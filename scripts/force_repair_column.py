import sys
import asyncio
import os
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import create_async_engine

# Ensure /app is in path
sys.path.insert(0, "/app")

from core.database import DATABASE_URL

async def repair():
    print("🔧 Starting Database Repair...")
    print(f"Target DB: {DATABASE_URL}")
    
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    async with engine.connect() as conn:
        # 1. Check if column exists strictly via PRAGMA
        print("Checking schema...")
        columns_res = await conn.execute(text("PRAGMA table_info(songs)"))
        columns = [row[1] for row in columns_res.fetchall()]
        
        if 'cover' in columns:
            print("✅ 'cover' column ALREADY EXISTS. No action needed.")
        else:
            print("❌ 'cover' column MISSING. Attempting to add it...")
            try:
                # 2. Add Column Manually
                await conn.execute(text("ALTER TABLE songs ADD COLUMN cover VARCHAR"))
                await conn.commit()
                print("✅ successfully executed: ALTER TABLE songs ADD COLUMN cover VARCHAR")
            except Exception as e:
                print(f"🔥 Repair Failed: {e}")
                
    # Double Check
    async with engine.connect() as conn:
        columns_res = await conn.execute(text("PRAGMA table_info(songs)"))
        columns = [row[1] for row in columns_res.fetchall()]
        if 'cover' in columns:
            print("🎉 Final Check: 'cover' column is PRESENT!")
        else:
            print("💀 Final Check: 'cover' column is STILL MISSING.")

if __name__ == "__main__":
    asyncio.run(repair())
