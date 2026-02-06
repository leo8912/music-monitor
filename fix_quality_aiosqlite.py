
import asyncio
import aiosqlite
import os
import json
import sys

async def fix_aiosqlite():
    db_relative = 'config/music_monitor.db'
    db_path = os.path.abspath(db_relative)
    
    print(f"Target DB: {db_path}")
    if not os.path.exists(db_path):
        print("DB File missing!")
        return

    async with aiosqlite.connect(db_path) as db:
        print("Connected.")
        
        async with db.execute("SELECT id, url, data_json FROM song_sources WHERE source='local'") as cursor:
            rows = await cursor.fetchall()
            
        updated = 0
        for row in rows:
            src_id, url, data_json_str = row
            if not url: continue
            
            ext = os.path.splitext(url)[1].lower()
            if ext in ['.flac', '.wav', '.ape', '.alac', '.aiff']:
                
                try:
                    data = json.loads(data_json_str) if data_json_str else {}
                except:
                    data = {}
                    
                if data.get('quality') != 'SQ':
                    print(f"Updating ID {src_id}: {data.get('quality')} -> SQ")
                    data['quality'] = 'SQ'
                    data['format'] = ext.replace('.', '').upper()
                    data['quality_details'] = f"{data['format']} | SQ"
                    
                    new_json = json.dumps(data, ensure_ascii=False)
                    await db.execute("UPDATE song_sources SET data_json=? WHERE id=?", (new_json, src_id))
                    updated += 1
        
        if updated > 0:
            await db.commit()
            print(f"Committed {updated} changes via aiosqlite.")
        else:
            print("No changes needed (already SQ).")

if __name__ == "__main__":
    asyncio.run(fix_aiosqlite())
