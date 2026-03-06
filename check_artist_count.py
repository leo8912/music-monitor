import asyncio
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from core.database import AsyncSessionLocal
from app.models.artist import Artist
from app.models.song import Song

async def test_artist_count():
    async with AsyncSessionLocal() as db:
        # 检查所有艺人状态
        stmt_all = select(Artist)
        res_all = await db.execute(stmt_all)
        all_artists = res_all.scalars().all()
        print(f"\nAll artists in DB: {len(all_artists)}")
        for a in all_artists:
            print(f"Name: {a.name}, ID: {a.id}, Monitored: {a.is_monitored}")

        stmt = (
            select(Artist, func.count(Song.id).label('song_count'))
            .options(selectinload(Artist.sources))
            .outerjoin(Song, Song.artist_id == Artist.id)
            .where(Artist.is_monitored == True)
            .group_by(Artist.id)
            .order_by(Artist.id.asc())
        )
        result = await db.execute(stmt)
        unique_rows = result.unique().all()
        print(f"\nMonitored artists with counts: {len(unique_rows)}")
        for a, count in unique_rows:
            print(f"Artist: {a.name}, ID: {a.id}, Count: {count}")

if __name__ == "__main__":
    asyncio.run(test_artist_count())
