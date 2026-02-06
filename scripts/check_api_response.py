import asyncio
import aiohttp
import sys

async def check_api():
    # Try localhost instead of IP
    base_url = "http://localhost:8000"
    login_url = f"{base_url}/api/login"
    library_url = f"{base_url}/api/library/songs"
    
    print(f"📡 API Check: {base_url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            # 1. Login
            print(f"🔑 Logging in...")
            login_data = {"username": "music", "password": "password"}
            async with session.post(login_url, json=login_data) as resp:
                if resp.status != 200:
                    print(f"❌ Login Failed: {resp.status}")
                    print(await resp.text())
                    return
                print("✅ Login Successful")
            
            # 2. Get Songs (Scan first 5 pages)
            found = False
            for page in range(1, 6):
                search_params = {"page": page, "page_size": 100}
                print(f"🔍 Requesting Page {page}: {library_url}")
                async with session.get(library_url, params=search_params) as resp:
                    if resp.status != 200:
                        print(f"❌ API Error: {resp.status}")
                        text = await resp.text()
                        print(text)
                        break 
                    
                    data = await resp.json()
                    items = data.get("items", [])
                    
                    target_items = [i for i in items if "一生所爱" in i.get('title', '')]
                    
                    if target_items:
                        print(f"✅ Found {len(target_items)} matching items on Page {page}!")
                        found = True
                        for item in target_items:
                            print(f"\n========================================")
                            print(f"🎵 API ITEM (ID: {item.get('id')})")
                            print(f"========================================")
                            print(f"Title: {item.get('title')}")
                            print(f"Artist: {item.get('artist')}")
                            print(f"Cover (Frontend): {item.get('cover')}")
                            print(f"Local Path: {item.get('local_path')}")
                            print(f"Source: {item.get('source')}")
                        break 
                    
                    if len(items) == 0:
                        print("⚠️ No more items, stopping.")
                        break

            if not found:
                 print("❌ Song not found in first 5 pages.")
                    
    except Exception as e:
        print(f"❌ Request Failed: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_api())
