import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song
from app.services.metadata_healer import MetadataHealer
from sqlalchemy import select

async def bulk_heal():
    print("🚀 Starting Bulk Cover Localization...")
    healer = MetadataHealer()
    
    async with AsyncSessionLocal() as db:
        # 查找所有持有 HTTP 封面的歌曲
        stmt = select(Song).where(Song.cover.like("http%"))
        result = await db.execute(stmt)
        songs = result.scalars().all()
        
        print(f"📊 Found {len(songs)} songs needing cover localization.")
        
        count = 0
        for song in songs:
            print(f"[{count+1}/{len(songs)}] Healing: {song.title}")
            try:
                # 此时 MetadataHealer 已修改为：即使 force=False 也会本地化 HTTP 封面
                success = await healer.heal_song(song.id, force=False)
                if success:
                    count += 1
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        print(f"\n✅ Completed. {count} songs localized.")

if __name__ == "__main__":
    asyncio.run(bulk_heal())
