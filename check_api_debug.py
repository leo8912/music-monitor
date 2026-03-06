import asyncio
import json
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from core.database import AsyncSessionLocal
from app.models.artist import Artist
from app.models.song import Song

async def debug_api_response():
    async with AsyncSessionLocal() as db:
        # 模拟 SubscriptionService.get_monitored_artists 的逻辑
        stmt = (
            select(Artist, func.count(Song.id).label('song_count'))
            .options(selectinload(Artist.sources))
            .outerjoin(Song, Song.artist_id == Artist.id)
            .where(Artist.is_monitored == True)
            .group_by(Artist.id)
            .order_by(Artist.id.asc())
        )
        result = await db.execute(stmt)
        artists_with_counts = result.unique().all()
        
        res = [
            {
                "name": a.name,
                "id": str(a.id),
                "source": "database",
                "sources": [s.source for s in a.sources] if a.sources else [],
                "avatar": a.avatar,
                "songCount": song_count or 0
            }
            for a, song_count in artists_with_counts
        ]
        print(json.dumps(res, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(debug_api_response())
