import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.getcwd())

from core.database import AsyncSessionLocal
from app.models.song import Song, SongSource
from sqlalchemy import select

async def final_audit():
    print("🕵️ Final Audit for Online Cover Links...")
    async with AsyncSessionLocal() as db:
        # 1. 检查 Song 表
        stmt = select(Song).where(Song.cover.like("http%"))
        res = await db.execute(stmt)
        http_songs = res.scalars().all()
        print(f"  - Song entries with HTTP cover: {len(http_songs)}")

        # 2. 检查 SongSource 表 (所有来源)
        stmt = select(SongSource).where(SongSource.cover.like("http%"))
        res = await db.execute(stmt)
        http_sources = res.scalars().all()
        # 排除非本地下载的歌曲 (如果歌曲根本没本地化，在线来源有 http 是正常的)
        # 但如果歌曲有 local_path，其所有 source 都不应该有 http

        suspicious = 0
        for src in http_sources:
            # 只有当该 SourceID 对应的 Song 有 local_path 时，才认为是异常
            res_song = await db.execute(select(Song).where(Song.id == src.song_id))
            song = res_song.scalar_one_or_none()
            if song and song.local_path:
                suspicious += 1
                # print(f"    🚩 Song ID {song.id} ({song.title}) has HTTP cover in source {src.source}")

        print(f"  - SongSource entries with HTTP cover (for localized songs): {suspicious}")

        # 3. 检查有没有 "潮汐锁定" 被遗漏的
        stmt = select(Song).where(Song.title.like("%潮汐锁定%"))
        res = await db.execute(stmt)
        songs = res.scalars().all()
        print(f"  - '潮汐锁定' records remaining with HTTP: {len([s for s in songs if s.cover and s.cover.startswith('http')])}")

    if len(http_songs) == 0 and suspicious == 0:
        print("\n✨ AUDIT PASSED: All localized songs use local cover art.")
    else:
        print("\n⚠️ AUDIT FAILED: Some inconsistencies remain.")

if __name__ == "__main__":
    asyncio.run(final_audit())
