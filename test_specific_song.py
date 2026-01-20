import asyncio
from qqmusic_api import singer

async def test_specific_song():
    # 李剑青的QQ音乐MID
    mid = "001BGUL33uMuK8"
    
    songs = await singer.get_songs(mid, num=100)
    
    print(f"总共返回 {len(songs)} 首歌\n")
    
    # 查找"乐人·live"这首歌
    target = None
    for song in songs:
        if "乐人" in song.get('name', '') or "live" in song.get('name', '').lower():
            target = song
            print(f"找到目标歌曲: {song.get('name')}")
            print(f"\n完整数据:")
            print(f"  mid: {song.get('mid')}")
            print(f"  name: {song.get('name')}")
            print(f"  time_public: '{song.get('time_public')}'")
            print(f"  album: {song.get('album')}")
            
            album = song.get('album', {})
            if isinstance(album, dict):
                print(f"\n  album详情:")
                print(f"    mid: {album.get('mid')}")
                print(f"    name: {album.get('name')}")
                print(f"    pmid: {album.get('pmid')}")
            print("\n" + "="*60)
            break
    
    if not target:
        print("未找到包含'乐人'或'live'的歌曲")
        print("\n前5首歌的标题:")
        for i, s in enumerate(songs[:5], 1):
            print(f"  {i}. {s.get('name')}")

asyncio.run(test_specific_song())
