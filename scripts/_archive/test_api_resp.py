import asyncio
import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.services.subscription import SubscriptionService
from sqlalchemy import select
from app.models.song import Song

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

async def test_api_output():
    async with AsyncSessionLocal() as db:
        stmt = select(Song).where(Song.title.like("%潮汐锁定%")).limit(1)
        res = await db.execute(stmt)
        song = res.scalar_one_or_none()

        if not song:
            print("❌ Song not found.")
            return

        artist_id = song.artist_id
        print(f"🕵️ Testing Artist ID: {artist_id} (Song: {song.title})")

        detail = await SubscriptionService.get_artist_detail(db, artist_id)

        found = False
        for s in detail.get('songs', []):
            if "潮汐锁定" in s.get('title', ''):
                print("\n✅ Found Song in API Response:")
                # Use encoder to handle datetime
                print(json.dumps(s, indent=2, ensure_ascii=False, cls=DateTimeEncoder))
                found = True

        if not found:
            print("❌ Song not found in artist detail songs.")

if __name__ == "__main__":
    asyncio.run(test_api_output())
