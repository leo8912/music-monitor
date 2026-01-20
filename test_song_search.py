import asyncio
from qqmusic_api import search
from qqmusic_api.search import SearchType

async def try_song_search():
    keyword = "李剑青"
    print(f"尝试通过歌曲搜索获取歌手信息: {keyword}")
    
    try:
        # SearchType.SONG = 0 (通常是默认)
        res = await search.search_by_type(keyword, search_type=SearchType.SONG, num=5)
        
        # 检查结构
        if isinstance(res, list) and len(res) > 0:
            first_song = res[0]
            print(f"第一首歌: {first_song.get('name')}")
            
            singers = first_song.get('singer', [])
            if singers:
                s = singers[0]
                print(f"找到歌手: {s.get('name')} (mid={s.get('mid')})")
            else:
                print("未找到歌手信息")
        else:
            print("搜索结果为空或格式不对")
            
    except Exception as e:
        print(f"SONG搜索失败: {e}")

if __name__ == "__main__":
    asyncio.run(try_song_search())
