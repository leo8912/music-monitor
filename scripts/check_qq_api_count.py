import asyncio
from qqmusic_api import singer

async def check_qq_api():
    # 李剑青的QQ音乐MID
    mid = "001BGUL33uMuK8"
    
    # 获取所有歌曲（默认最多500首）
    songs = await singer.get_songs(mid, num=500)
    
    print(f"QQ音乐API返回: {len(songs)} 首歌曲")
    print(f"官网显示: 34 首单曲\n")
    
    if len(songs) != 34:
        print(f"⚠️ 数量不一致！差异: {abs(len(songs) - 34)} 首\n")
    else:
        print("✅ 数量一致\n")
    
    print("API返回的歌曲列表（前10首）:")
    for i, song in enumerate(songs[:10], 1):
        print(f"{i:2d}. {song.get('name')}")

asyncio.run(check_qq_api())
