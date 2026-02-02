
import asyncio
import aiohttp
import json

async def probe_search_raw(keyword):
    url = "https://music-api.gdstudio.xyz/api.php"
    params = {
        "types": "search",
        "count": 5,
        "source": "kuwo",
        "pages": 1,
        "name": keyword
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            print(f"--- Search Results for '{keyword}' ---")
            for i, item in enumerate(data):
                print(f"Item {i}:")
                print(f"  Title: {item.get('name')}")
                print(f"  Pic: {item.get('pic')}")
                print(f"  Pic ID: {item.get('pic_id')}")
                print("-" * 20)

if __name__ == "__main__":
    asyncio.run(probe_search_raw("困"))
    asyncio.run(probe_search_raw("稻香"))
