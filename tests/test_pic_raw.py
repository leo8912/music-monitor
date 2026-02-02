
import asyncio
import aiohttp
import json

async def test_pic_content():
    url = "https://music-api.gdstudio.xyz/api.php?types=pic&source=netease&id=2651425710&size=500"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            print(f"Status: {resp.status}")
            print(f"Content-Type: {resp.headers.get('Content-Type')}")
            try:
                data = await resp.json()
                print(f"JSON Data: {json.dumps(data, indent=2)}")
            except:
                text = await resp.text()
                print(f"Text Content (first 100 chars): {text[:100]}")

if __name__ == "__main__":
    asyncio.run(test_pic_content())
