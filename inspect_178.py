
import asyncio
import aiosqlite
import os

async def inspect_178():
    db_path = os.path.abspath('config/music_monitor.db')
    print(f"DB: {db_path}")
    
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT id, song_id, source, source_id, url, data_json FROM song_sources WHERE id=178") as cursor:
            row = await cursor.fetchone()
            
            if row:
                print(f"ID: {row[0]}")
                print(f"Song ID: {row[1]}")
                print(f"Source: {row[2]}")
                print(f"Source ID: {row[3]}")
                print(f"URL: '{row[4]}'") # Quote to see whitespace/empty
                print(f"Data: {row[5]}")
            else:
                print("Source 178 not found via SQL.")

if __name__ == "__main__":
    asyncio.run(inspect_178())
