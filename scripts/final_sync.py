import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def sync_all():
    print("🚀 Starting global SongSource cover sync...")
    async with AsyncSessionLocal() as db:
        # 获取所有已本地化封面的歌曲
        stmt = select(Song).options(selectinload(Song.sources)).where(Song.cover.like("/uploads/%"))
        result = await db.execute(stmt)
        songs = result.scalars().all()
        
        print(f"📊 Processed {len(songs)} songs.")
        
        updated_sources = 0
        for s in songs:
            for src in s.sources:
                if src.cover != s.cover:
                    src.cover = s.cover
                    updated_sources += 1
                
                # 同步 data_json
                if src.data_json:
                    import json
                    try:
                        data = src.data_json
                        if isinstance(data, str):
                            data = json.loads(data)
                        
                        if isinstance(data, dict) and data.get("cover") != s.cover:
                            data["cover"] = s.cover
                            src.data_json = data
                            updated_sources += 1
                    except:
                        pass
        
        await db.commit()
        print(f"✅ Synced {updated_sources} source fields across {len(songs)} songs.")

if __name__ == "__main__":
    asyncio.run(sync_all())
