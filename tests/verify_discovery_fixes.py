
import asyncio
import aiohttp
import sys

async def verify_fixes():
    # We call the endpoints on the running server at http://localhost:8000
    base_url = "http://localhost:8000/api/discovery"
    
    async with aiohttp.ClientSession() as session:
        # 1. Verify Probe Qualities (Fixes NameError: DownloadService)
        print("Testing Probe Qualities...")
        params = {"source": "netease", "id": "2651425710"}
        async with session.get(f"{base_url}/probe_qualities", params=params) as resp:
            print(f"  Status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                print(f"  Success! Found {len(data)} qualities.")
            else:
                text = await resp.text()
                print(f"  Failed: {text}")

        # 2. Verify Cover Proxy (Fixes Missing Covers)
        print("\nTesting Cover Proxy...")
        params = {"source": "netease", "id": "2651425710"}
        async with session.get(f"{base_url}/cover", params=params, allow_redirects=False) as resp:
            print(f"  Status: {resp.status}")
            if resp.status in [301, 302, 303, 307, 308]:
                location = resp.headers.get("Location")
                print(f"  Success! Redirected to: {location}")
            else:
                text = await resp.text()
                print(f"  Failed: {text}")

if __name__ == "__main__":
    try:
        asyncio.run(verify_fixes())
    except Exception as e:
        print(f"Could not connect to server: {e}")
        print("Make sure 'python main.py' is running.")
