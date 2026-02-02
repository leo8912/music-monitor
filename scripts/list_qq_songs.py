import asyncio
from qqmusic_api import singer

async def list_all_qq_songs():
    # 李剑青 MID
    mid = "001BGUL33uMuK8"
    
    print(f"正在从QQ音乐API获取歌手 [mid={mid}] 的歌曲列表...\n")
    
    # 获取歌曲
    songs = await singer.get_songs(mid, num=100)
    
    print(f"API共返回: {len(songs)} 首\n")
    print(f"{'序号':<4} | {'歌曲名':<30} | {'专辑':<20} | {'Mid'}")
    print("-" * 80)
    
    for i, song in enumerate(songs, 1):
        name = song.get('name', '').strip()
        album = song.get('album', {}).get('name', '')
        mid = song.get('mid', '')
        print(f"{i:<4} | {name:<30} | {album:<20} | {mid}")

if __name__ == "__main__":
    asyncio.run(list_all_qq_songs())
