"""
测试艺人详情API端点

运行: python 测试/后端/test_artist_detail.py
"""
import asyncio
import sys
sys.path.insert(0, '.')

from core.database import AsyncSessionLocal
from app.services.subscription import SubscriptionService

async def test_artist_detail():
    async with AsyncSessionLocal() as db:
        # 1. 获取所有关注的艺人
        artists = await SubscriptionService.get_monitored_artists(db)
        
        if not artists:
            print("❌ 没有关注的艺人，请先添加艺人")
            return
        
        print(f"✅ 找到 {len(artists)} 个关注的艺人\n")
        
        # 2. 测试第一个艺人的详情
        test_artist = artists[0]
        artist_id = int(test_artist['id'])
        artist_name = test_artist['name']
        
        print(f"📋 测试艺人: {artist_name} (ID: {artist_id})")
        print("-" * 50)
        
        detail = await SubscriptionService.get_artist_detail(db, artist_id)
        
        if not detail:
            print(f"❌ 无法获取艺人详情")
            return
        
        # 3. 验证返回数据
        print(f"✅ 艺人名称: {detail['name']}")
        print(f"✅ 头像: {detail['avatar'][:50] if detail['avatar'] else '无'}...")
        print(f"✅ 来源平台: {', '.join(detail['sources'])}")
        print(f"✅ 歌曲数量: {len(detail['songs'])}")
        print(f"✅ 专辑数量: {len(detail['albums'])}")
        
        # 4. 显示前3首歌曲
        if detail['songs']:
            print(f"\n📀 前3首歌曲:")
            for i, song in enumerate(detail['songs'][:3], 1):
                sources = ', '.join([s['source'] for s in song['sources']])
                print(f"  {i}. {song['title']} - {song['artist']}")
                print(f"     专辑: {song['album'] or '未知'} | 来源: {sources}")
        
        # 5. 显示前3张专辑
        if detail['albums']:
            print(f"\n💿 前3张专辑:")
            for i, album in enumerate(detail['albums'][:3], 1):
                print(f"  {i}. {album['name']} ({album['publishTime'][:4] if album['publishTime'] else '未知'})")
        
        print("\n" + "=" * 50)
        print("✅ 测试通过！艺人详情API工作正常")

if __name__ == "__main__":
    asyncio.run(test_artist_detail())
