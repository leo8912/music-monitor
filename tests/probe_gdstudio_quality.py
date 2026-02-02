
import asyncio
import aiohttp
import json

API_BASE = "https://music-api.gdstudio.xyz/api.php"

async def probe_quality(session, source, track_id, br):
    params = {
        "types": "url",
        "source": source,
        "id": track_id,
        "br": br
    }
    try:
        async with session.get(API_BASE, params=params, timeout=10) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data and data.get("url"):
                    return {"br": br, "actual_br": data.get("br"), "size": data.get("size"), "available": True}
            return {"br": br, "available": False, "status": resp.status}
    except Exception as e:
        return {"br": br, "available": False, "error": str(e)}

async def main():
    # Test for netease:2651425710
    source = "netease"
    track_id = "2651425710"
    
    # Also test a netease one for comparison
    # source = "netease"
    # track_id = "2651425710"
    
    qualities = [128, 192, 320, 740, 999]
    
    async with aiohttp.ClientSession() as session:
        tasks = [probe_quality(session, source, track_id, q) for q in qualities]
        results = await asyncio.gather(*tasks)
        
        print(f"Results for {source}:{track_id}")
        for r in results:
            print(r)

if __name__ == "__main__":
    asyncio.run(main())
