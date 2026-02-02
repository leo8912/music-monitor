import sys
import os
import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Add root directory to sys.path
sys.path.append(os.getcwd())

try:
    from app.models.song import Song, SongSource
    from core.database import AsyncSessionLocal
except ImportError as e:
    print(f"Initial import failed: {e}")
    # Fallback or re-try with explicit path if needed, 
    # but sys.path.append(os.getcwd()) should handle d:\code\music-monitor
    raise e

async def fix_data():
    async with AsyncSessionLocal() as db:
        print("开始扫描脏数据...")
        
        # 1. Cleaning Song table
        result = await db.execute(select(Song))
        songs = result.scalars().all()
        
        dirty_songs = 0
        for s in songs:
            changed = False
            if s.cover and ('\n' in s.cover or '\r' in s.cover or s.cover.strip() != s.cover):
                print(f"Fixing Song {s.id} cover: {repr(s.cover)} -> {repr(s.cover.strip())}")
                s.cover = s.cover.strip()
                changed = True
            
            if s.title and ('\n' in s.title or '\r' in s.title or s.title.strip() != s.title):
                print(f"Fixing Song {s.id} title: {repr(s.title)} -> {repr(s.title.strip())}")
                s.title = s.title.strip()
                changed = True
                
            if changed:
                dirty_songs += 1
                
        print(f"发现并清理了 {dirty_songs} 个 Song 记录")
        
        # 2. Cleaning SongSource table
        result = await db.execute(select(SongSource))
        sources = result.scalars().all()
        
        dirty_sources = 0
        for src in sources:
            changed = False
            # Fix Source ID (CRITICAL for scanning)
            if src.source_id and ('\n' in src.source_id or '\r' in src.source_id or src.source_id.strip() != src.source_id):
                 print(f"Fixing Source {src.id} source_id: {repr(src.source_id)} -> {repr(src.source_id.strip())}")
                 src.source_id = src.source_id.strip()
                 changed = True

            # Fix Cover
            if src.cover and ('\n' in src.cover or '\r' in src.cover or src.cover.strip() != src.cover):
                print(f"Fixing Source {src.id} cover: {repr(src.cover)} -> {repr(src.cover.strip())}")
                src.cover = src.cover.strip()
                changed = True
            
            # Fix JSON data
            if src.data_json and isinstance(src.data_json, dict):
                dj = src.data_json
                if 'cover' in dj:
                    c = dj['cover']
                    if c and isinstance(c, str) and ('\n' in c or '\r' in c or c.strip() != c):
                        print(f"Fixing Source {src.id} JSON cover")
                        dj['cover'] = c.strip()
                        src.data_json = dict(dj) # Force update
                        changed = True
            
            if changed:
                dirty_sources += 1
        
        print(f"发现并清理了 {dirty_sources} 个 Source 记录")
        
        if dirty_songs > 0 or dirty_sources > 0:
            await db.commit()
            print("✅ 数据库清洗完成并提交")
        else:
            print("✨ 数据库很干净，无需清理")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(fix_data())
