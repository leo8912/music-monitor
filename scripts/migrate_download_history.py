"""
下载历史数据迁移脚本
将现有MediaRecord表中的下载相关数据迁移到新的DownloadHistory表
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from core.database import AsyncSessionLocal, async_init_db, MediaRecord
from app.models.download_history import DownloadHistory
from app.services.download_history_service import DownloadHistoryService


async def migrate_download_history():
    """迁移下载历史数据"""
    # 初始化数据库
    await async_init_db()
    
    async with AsyncSessionLocal() as session:
        print("正在查询现有MediaRecord数据...")
        
        # 查询所有MediaRecord记录
        stmt = select(MediaRecord)
        result = await session.execute(stmt)
        media_records = result.scalars().all()
        
        print(f"找到 {len(media_records)} 条MediaRecord记录")
        
        migrated_count = 0
        for record in media_records:
            # 检查是否已经有对应的下载历史记录
            existing_stmt = select(DownloadHistory).where(
                DownloadHistory.song_unique_key == record.unique_key
            )
            existing_result = await session.execute(existing_stmt)
            existing_history = existing_result.scalars().first()
            
            if existing_history:
                print(f"跳过已存在的记录: {record.title}")
                continue
            
            # 确定下载状态
            download_status = 'SUCCESS' if record.local_audio_path else 'FAILED'
            
            # 创建下载历史记录
            history_record = DownloadHistory(
                song_unique_key=record.unique_key,
                title=record.title,
                artist=record.author,
                album=record.album,
                source=record.source,
                source_id=record.media_id,
                download_path=record.local_audio_path,
                download_status=download_status,
                download_time=record.found_at,
                download_duration=None,  # 原数据中没有此项
                file_size=None,  # 原数据中没有此项
                quality=None,  # 原数据中没有此项
                error_message=None  # 原数据中没有此项
            )
            
            session.add(history_record)
            migrated_count += 1
            
            if migrated_count % 50 == 0:  # 每50条提交一次，避免内存占用过大
                await session.commit()
                print(f"已迁移 {migrated_count} 条记录...")
        
        # 提交剩余记录
        await session.commit()
        print(f"数据迁移完成！共迁移 {migrated_count} 条记录")


if __name__ == "__main__":
    asyncio.run(migrate_download_history())