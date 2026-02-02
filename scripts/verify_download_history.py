"""
验证下载历史API集成
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from core.database import AsyncSessionLocal, async_init_db
from app.models.download_history import DownloadHistory
from app.services.download_history_service import DownloadHistoryService


async def verify_integration():
    """验证下载历史功能集成"""
    # 初始化数据库
    await async_init_db()
    
    async with AsyncSessionLocal() as session:
        # 获取下载历史记录数量
        stmt = select(DownloadHistory)
        result = await session.execute(stmt)
        records = result.scalars().all()
        
        print(f"当前数据库中有 {len(records)} 条下载历史记录")
        
        if records:
            print("最近的几条记录:")
            for i, record in enumerate(records[-5:]):  # 显示最后5条记录
                print(f"  {i+1}. {record.title} by {record.artist} - {record.download_status} ({record.download_time})")
        
        # 测试服务功能
        service = DownloadHistoryService()
        
        # 添加一个新的下载历史记录进行测试
        print("\n正在添加测试记录...")
        new_record = await service.log_download_attempt(
            db=session,
            title="集成测试歌曲",
            artist="集成测试歌手",
            album="集成测试专辑",
            source="integration_test",
            source_id="test_001",
            status="SUCCESS",
            download_path="/test/path/integration_test.mp3"
        )
        
        print(f"新增记录ID: {new_record.id}")
        
        # 查询刚才添加的记录
        stmt = select(DownloadHistory).where(DownloadHistory.id == new_record.id)
        result = await session.execute(stmt)
        fetched_record = result.scalar_one_or_none()
        
        if fetched_record:
            print(f"验证成功: {fetched_record.title} - {fetched_record.download_status}")
        else:
            print("验证失败: 未能找到刚添加的记录")


if __name__ == "__main__":
    asyncio.run(verify_integration())