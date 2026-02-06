
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import AsyncSessionLocal
from app.services.subscription import SubscriptionService
import json

async def test_api_call(artist_id):
    async with AsyncSessionLocal() as db:
        try:
            print(f"Calling get_artist_detail for id {artist_id}...")
            detail = await SubscriptionService.get_artist_detail(db, artist_id)
            if detail:
                print("Success! Result keys:", detail.keys())
                print("First song example:", detail['songs'][0] if detail['songs'] else "No songs")
                # Try to JSON serialize it, as FastAPI would
                json_data = json.dumps(detail, default=str)
                print("JSON serialization worked.")
            else:
                print("Artist not found.")
        except Exception as e:
            import traceback
            print("ERROR:")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api_call(4))
