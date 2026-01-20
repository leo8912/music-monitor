import asyncio
from qqmusic_api import search
from qqmusic_api.search import SearchType

async def test_search():
    keyword = "李剑青"
    print(f"正在搜索: {keyword} ...")
    try:
        # 尝试 SearchType.SINGER (type 2)
        res = await search.search_by_type(keyword, search_type=SearchType.SINGER, num=3)
        print("搜索结果 (SINGER):")
        print(res)
    except Exception as e:
        print(f"搜索失败 (SINGER): {e}")

    print("-" * 40)
    
    try:
        # 尝试默认搜索 (SONG/Smart)
        res = await search.search_by_type(keyword, search_type=SearchType.SONG, num=3)
        print("搜索结果 (SONG):")
        if isinstance(res, list) and res:
            print(f"找到 {len(res)} 首歌")
            print(res[0])
    except Exception as e:
        print(f"搜索失败 (SONG): {e}")

if __name__ == "__main__":
    asyncio.run(test_search())
