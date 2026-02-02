import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import select, func, delete
from core.database import AsyncSessionLocal
from app.models.song import SongSource

async def cleanup_duplicates():
    async with AsyncSessionLocal() as db:
        print("--- 正在启动数据库去重清理任务 ---")
        
        # Step 1: Find all duplicate groups
        stmt = select(
            SongSource.song_id, 
            SongSource.source, 
            SongSource.source_id
        ).group_by(
            SongSource.song_id, 
            SongSource.source, 
            SongSource.source_id
        ).having(func.count(SongSource.id) > 1)
        
        duplicates = (await db.execute(stmt)).all()
        
        if not duplicates:
            print("✅ 数据库中未发现重复记录。")
            return
            
        print(f"发现 {len(duplicates)} 组重复来源信息。")
        
        total_deleted = 0
        for r in duplicates:
            # For each duplicate group, keep the one with the smallest ID and delete the rest
            detail_stmt = select(SongSource.id).where(
                SongSource.song_id == r.song_id,
                SongSource.source == r.source,
                SongSource.source_id == r.source_id
            ).order_by(SongSource.id.asc())
            
            all_ids = (await db.execute(detail_stmt)).scalars().all()
            
            if len(all_ids) > 1:
                # Keep first, delete others
                to_delete = all_ids[1:]
                del_stmt = delete(SongSource).where(SongSource.id.in_(to_delete))
                await db.execute(del_stmt)
                total_deleted += len(to_delete)
                print(f"  - 歌曲 ID {r.song_id} ({r.source}): 保留 ID {all_ids[0]}, 删除重复项 {to_delete}")
        
        await db.commit()
        print(f"\n✨ 清理完毕！共删除 {total_deleted} 条冗余记录。")

if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())
