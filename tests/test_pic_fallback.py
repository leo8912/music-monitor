
import asyncio
import aiohttp

async def test_pic_fallback():
    url = "https://music-api.gdstudio.xyz/api.php"
    # Netease "稻香" ID: 2651425710
    # Kuwo "困" ID: 518930167
    tests = [
        {"source": "netease", "id": "2651425710"},
        {"source": "kuwo", "id": "518930167"}
    ]
    
    async with aiohttp.ClientSession() as session:
        for t in tests:
            pic_url = f"{url}?types=pic&source={t['source']}&id={t['id']}&size=500"
            print(f"Testing PIC URL: {pic_url}")
            async with session.get(pic_url) as resp:
                print(f"  Status: {resp.status}")
                if resp.status == 200:
                    content_type = resp.headers.get("Content-Type", "")
                    print(f"  Content-Type: {content_type}")
                    # If it's an image, it should have image/* content type
                    # Some APIs return a redirect or a 404 if no pic

if __name__ == "__main__":
    asyncio.run(test_pic_fallback())
