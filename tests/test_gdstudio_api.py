
import asyncio
import aiohttp
import json

API_BASE = "https://music-api.gdstudio.xyz/api.php"

async def test_source(session, source, keyword="稻香"):
    params = {
        "types": "search",
        "source": source,
        "name": keyword,
        "count": 1,
        "pages": 1
    }
    try:
        async with session.get(API_BASE, params=params, timeout=10) as resp:
            status = resp.status
            try:
                data = await resp.json()
                is_json = True
            except:
                data = await resp.text()
                is_json = False
            
            return {
                "source": source,
                "status": status,
                "is_json": is_json,
                "data_preview": str(data)[:100] if is_json else "Non-JSON response"
            }
    except Exception as e:
        return {"source": source, "status": "Error", "error": str(e)}

async def main():
    sources = ["netease", "tencent", "tidal", "spotify", "ytmusic", "qobuz", "joox", "deezer", "migu", "kugou", "kuwo", "ximalaya", "apple"]
    
    async with aiohttp.ClientSession() as session:
        tasks = [test_source(session, s) for s in sources]
        results = await asyncio.gather(*tasks)
        
        print(f"{'Source':<12} | {'Status':<8} | {'Preview'}")
        print("-" * 50)
        for r in results:
            preview = r.get("data_preview", r.get("error", "N/A"))
            print(f"{r['source']:<12} | {r['status']:<8} | {preview}")

if __name__ == "__main__":
    asyncio.run(main())
