"""
模拟API返回的去重逻辑，检查分页结果
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, desc
from core.database import AsyncSessionLocal, MediaRecord


async def simulate_api_response():
    """模拟API响应中的去重逻辑"""
    async with AsyncSessionLocal() as session:
        # 模拟API中的查询逻辑
        query = select(MediaRecord).order_by(desc(MediaRecord.publish_time), desc(MediaRecord.found_at))
        result = await session.execute(query)
        records = result.scalars().all()
        
        print(f"数据库总记录数: {len(records)}")
        
        # 实现API中的去重逻辑
        unique_items_map = {}
        for record in records:
            # 使用标题、作者和专辑作为唯一标识（这是现在的逻辑）
            unique_key_combo = f"{record.title}_{record.author}_{record.album}".lower()
            
            if unique_key_combo in unique_items_map:
                # 如果已存在相同歌曲，合并平台信息
                existing_item = unique_items_map[unique_key_combo]
                
                # 收集额外的来源平台
                extra_sources = set()
                if existing_item['extra_sources']:
                    if isinstance(existing_item['extra_sources'], list):
                        extra_sources.update(existing_item['extra_sources'])
                    else:
                        try:
                            import json
                            parsed = json.loads(existing_item['extra_sources'])
                            if isinstance(parsed, list):
                                extra_sources.update(parsed)
                        except:
                            extra_sources.add(existing_item['source'])

                # 添加当前记录的源作为额外源，但要避免重复添加主平台
                if record.source != existing_item['source']:  # 确保不是主平台
                    extra_sources.add(record.source)
                existing_item['extra_sources'] = list(extra_sources)
                
                # 保持最新的时间戳
                record_time = record.found_at.isoformat() if record.found_at else None
                if record_time and (not existing_item['found_at'] or record_time > existing_item['found_at']):
                    existing_item['found_at'] = record_time
                    existing_item['created_at'] = record_time
                
                # 更新最新的发布时间（如果当前记录的发布时间更晚）
                record_pub_time = record.publish_time.isoformat() if record.publish_time else None
                existing_pub_time = existing_item['publish_time']
                if record_pub_time and existing_pub_time and record_pub_time > existing_pub_time:
                    existing_item['publish_time'] = record_pub_time
                elif record_pub_time and not existing_pub_time:
                    existing_item['publish_time'] = record_pub_time
                    
            else:
                # 新增项目
                item = {
                    'id': record.id,
                    'unique_key': record.unique_key,
                    'source': record.source,
                    'media_type': record.media_type,
                    'media_id': record.media_id,
                    'title': record.title,
                    'author': record.author,
                    'artist': record.author,  # 兼容前端字段
                    'cover': getattr(record, 'cover', None),
                    'cover_url': getattr(record, 'cover', None),  # 兼容前端字段
                    'url': getattr(record, 'url', None),
                    'trial_url': getattr(record, 'trial_url', None),
                    'album': getattr(record, 'album', ''),
                    'publish_time': record.publish_time.isoformat() if record.publish_time else None,
                    'found_at': record.found_at.isoformat() if record.found_at else None,
                    'local_audio_path': getattr(record, 'local_path', None),
                    'is_favorite': getattr(record, 'is_favorite', False),
                    'extra_sources': [],  # 初始为空，避免主平台被重复添加到额外平台列表,
                    'created_at': record.found_at.isoformat() if record.found_at else None,
                }
                unique_items_map[unique_key_combo] = item
        
        # 转换为列表并按时间排序
        items = list(unique_items_map.values())
        
        # 按publish_time（发布时间）降序排序（最新发布在前），如果发布时间为空则按发现时间排序
        items.sort(key=lambda x: x['publish_time'] or x['found_at'] or x['created_at'] or '', reverse=True)
        
        print(f"去重后的歌曲数量: {len(items)}")
        
        # 模拟分页
        limit = 20  # 每页20首
        total_pages = (len(items) + limit - 1) // limit  # 向上取整
        print(f"每页显示 {limit} 首歌曲")
        print(f"总共需要 {total_pages} 页")
        
        # 检查总数计算逻辑
        # 重新计算总数（模拟API中的逻辑）
        all_records = records  # 这里是所有记录
        unique_items_map_total = {}
        for record in all_records:
            # 使用标题、作者和专辑作为唯一标识
            unique_key_combo = f"{record.title}_{record.author}_{record.album}".lower()
            
            if unique_key_combo not in unique_items_map_total:
                # 只有当唯一标识不存在时才添加
                unique_items_map_total[unique_key_combo] = record
        
        calculated_total = len(unique_items_map_total)
        print(f"API中计算的总数: {calculated_total}")
        
        return items


if __name__ == "__main__":
    asyncio.run(simulate_api_response())