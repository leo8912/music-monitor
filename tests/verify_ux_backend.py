
import asyncio
import aiohttp
import sys

async def verify_ux_backend():
    base_url = "http://localhost:8000/api/library"
    
    # Prerequisite: Have a song in the library. 
    # Validating "稻香" (netease:2651425710)
    # We need its internal database ID.
    
    async with aiohttp.ClientSession() as session:
        # 1. Fetch library to find a song ID
        print("Fetching library songs...")
        async with session.get(f"{base_url}/songs?limit=1") as resp:
            if resp.status != 200:
                print(f"Failed to fetch library: {await resp.text()}")
                return
            data = await resp.json()
            items = data.get("items", [])
            if not items:
                print("Library is empty.")
                return
            
            target_song = items[0]
            song_id = target_song["id"]
            print(f"Target Song: {target_song['title']} (ID: {song_id})")

        # 2. Test Redownload API response
        print(f"\nTesting Redownload API for Song ID: {song_id}...")
        payload = {
            "song_id": song_id,
            "source": "netease",
            "track_id": "2651425710",
            "quality": 320 # Low quality for fast test
        }
        
        async with session.post(f"{base_url}/redownload", json=payload) as resp:
            print(f"  Status: {resp.status}")
            if resp.status == 200:
                result = await resp.json()
                print(f"  Success: {result.get('success')}")
                if "song" in result:
                    song = result["song"]
                    print("  Received updated song metadata!")
                    print(f"    New Path: {song.get('local_path')}")
                    print(f"    New Title: {song.get('title')}")
                else:
                    print("  ERROR: Updated song metadata missing from response!")
            else:
                print(f"  Failed: {await resp.text()}")

if __name__ == "__main__":
    asyncio.run(verify_ux_backend())
