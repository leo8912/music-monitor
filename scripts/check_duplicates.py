"""
检查数据库中的重复记录情况
用于分析当前去重逻辑的效果
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import select
from core.database import AsyncSessionLocal, MediaRecord


async def check_duplicates():
    """检查数据库中的重复记录"""
    async with AsyncSessionLocal() as session:
        # 获取所有记录
        result = await session.execute(select(MediaRecord))
        records = result.scalars().all()
        
        print(f"总记录数: {len(records)}")
        
        # 按旧逻辑统计（仅标题+作者）
        old_dedup_map = {}
        for record in records:
            unique_key = f"{record.title}_{record.author}".lower()
            if unique_key not in old_dedup_map:
                old_dedup_map[unique_key] = []
            old_dedup_map[unique_key].append(record)
        
        print(f"按旧逻辑（标题+作者）去重后歌曲数: {len(old_dedup_map)}")
        
        # 按新逻辑统计（标题+作者+专辑）
        new_dedup_map = {}
        for record in records:
            unique_key = f"{record.title}_{record.author}_{record.album}".lower()
            if unique_key not in new_dedup_map:
                new_dedup_map[unique_key] = []
            new_dedup_map[unique_key].append(record)
        
        print(f"按新逻辑（标题+作者+专辑）去重后歌曲数: {len(new_dedup_map)}")
        
        # 显示一些重复的示例
        print("\n=== 旧逻辑下的重复记录示例 ===")
        old_duplicates = {k: v for k, v in old_dedup_map.items() if len(v) > 1}
        count = 0
        for unique_key, records_list in old_duplicates.items():
            if count >= 5:  # 只显示前5个重复项
                break
            print(f"重复项: {unique_key}")
            for record in records_list:
                print(f"  - ID: {record.id}, 来源: {record.source}, 专辑: {record.album or 'N/A'}, 时间: {record.publish_time}")
            count += 1
        
        print("\n=== 新逻辑下的重复记录示例 ===")
        new_duplicates = {k: v for k, v in new_dedup_map.items() if len(v) > 1}
        count = 0
        for unique_key, records_list in new_duplicates.items():
            if count >= 5:  # 只显示前5个重复项
                break
            print(f"重复项: {unique_key}")
            for record in records_list:
                print(f"  - ID: {record.id}, 来源: {record.source}, 专辑: {record.album or 'N/A'}, 时间: {record.publish_time}")
            count += 1


if __name__ == "__main__":
    asyncio.run(check_duplicates())