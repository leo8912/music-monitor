import asyncio
from plugins.qqmusic import QQMusicMonitor

async def test_plugin():
    monitor = QQMusicMonitor()
    # 李剑青的QQ音乐MID
    mid = "001BGUL33uMuK8"
    
    songs = await monitor.get_new_content(mid, "李剑青")
    
    print(f"插件返回 {len(songs)} 首歌曲\n")
    
    for i, song in enumerate(songs[:3], 1):
        print(f"{i}. {song.title}")
        print(f"   封面: {song.cover_url[:60] if song.cover_url else '❌ 无'}")
        print(f"   专辑: {song.album if song.album else '❌ 无'}")  
        print(f"   发布: {song.publish_time}")
        print()

asyncio.run(test_plugin())
