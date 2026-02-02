
import asyncio
import logging
import sys
import os
import json
from unittest.mock import MagicMock, AsyncMock, patch

# Add project root to path
sys.path.append(os.getcwd())

# Dummy SearchResult to simulate DownloadService output
class SearchResult:
    def __init__(self, id, source, title, artist, album, weight_score=0):
        self.id = id
        self.source = source
        self.title = title
        self.artist = artist
        self.album = album
        self.weight_score = weight_score

async def test_search_download():
    print("--- Testing GDStudio Search Aggregation Logic ---")
    
    try:
        from app.routers.discovery import search_download
        
        # Mock DownloadService
        with patch('app.services.download_service.DownloadService') as MockDSClass:
            mock_ds = MockDSClass.return_value
            
            # Setup mock search results for different sources
            mock_ds.search_single_source = AsyncMock(side_effect=[
                [SearchResult("kw1", "kuwo", "Title 1", ["Artist A"], "Album X", 1000)],
                [SearchResult("ne1", "netease", "Title 1", ["Artist A"], "Album X", 800)],
                [SearchResult("kg1", "kugou", "Title 1", ["Artist A"], "Album X", 600)],
                [SearchResult("tx1", "tencent", "Title 1", ["Artist A"], "Album X", 400)]
            ])
            
            # Call the router function (Directly call the function, bypassing FastAPI dependency injection if any)
            # Actually search_download uses Query(...) but we can just call it with keyword/limit
            print("Calling search_download endpoint logic...")
            results = await search_download(keyword="Artist A - Title 1", limit=5)
            
            print(f"Received {len(results)} results.")
            
            # Verify structure and content
            for i, r in enumerate(results):
                print(f"[{i+1}] {r['source']}:{r['id']} - {r['title']} - {r['artist']} (Score via Sort)")
                
            if len(results) > 0:
                print("✅ search_download logic confirmed.")
                # Verify sorting (first should be kw1 with 1000 score)
                if results[0]['id'] == "kw1":
                    print("✅ Results correctly sorted by weight score.")
                else:
                    print(f"❌ Sorting failed. Top result: {results[0]['id']}")
            else:
                print("❌ No results returned.")
                
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_search_download())
