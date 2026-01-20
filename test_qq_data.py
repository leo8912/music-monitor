import asyncio
from qqmusic_api import singer

async def test_qq_songs():
    # 李剑青的QQ音乐MID
    mid = "001BGUL33uMuK8"
    
    songs = await singer.get_songs(mid, num=5)
    
    print(f"返回类型: {type(songs)}")
    print(f"歌曲数量: {len(songs) if isinstance(songs, list) else 'N/A'}\n")
    
    if isinstance(songs, list):
        for i, song in enumerate(songs[:3], 1):
            print(f"{i}. {song.get('name', 'N/A')}")
            print(f"   time_public: {song.get('time_public', 'MISSING')}")
            print(f"   album: {song.get('album')}")
            album = song.get('album', {})
            if isinstance(album, dict):
                print(f"   album.mid: {album.get('mid', 'N/A')}")
                print(f"   album.name: {album.get('name', 'N/A')}")
            print()

asyncio.run(test_qq_songs())
