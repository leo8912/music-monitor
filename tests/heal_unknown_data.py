
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from core.database import AsyncSessionLocal
from app.models.song import Song
from app.models.artist import Artist
from app.services.scan_service import ScanService
from app.repositories.artist import ArtistRepository

async def heal_unknown_data():
    async with AsyncSessionLocal() as db:
        # 1. 寻找所有关联到 "未知歌手" (或类似名称) 的歌曲
        stmt = select(Song).options(selectinload(Song.artist)).join(Artist).where(
            Artist.name.in_(["未知歌手", "Unknown Artist", "Unknown", "未知"]),
            Song.local_path.isnot(None)
        )
        result = await db.execute(stmt)
        songs = result.scalars().all()
        
        if not songs:
            print("No songs found needing healing.")
            return

        print(f"Healing {len(songs)} songs...")
        scan_service = ScanService()
        artist_repo = ArtistRepository(db)
        
        for song in songs:
            print(f"  Processing: {song.title} (Path: {song.local_path})")
            filename = os.path.basename(song.local_path)
            
            # 使用新的修复逻辑进行解析
            # 注意: 我们主要想修复歌手名
            meta = await scan_service._extract_metadata(song.local_path, filename)
            
            new_artist_name = meta.get('artist')
            new_title = meta.get('title')
            
            if new_artist_name and new_artist_name not in ["Unknown Artist", "Unknown", "未知歌手", "未知"]:
                print(f"    -> Found correct artist: {new_artist_name}")
                
                # 获取或创建正确的 Artist 对象
                artist_obj = await artist_repo.get_or_create_by_name(new_artist_name)
                song.artist_id = artist_obj.id
                song.title = new_title or song.title
                
                # 更新封面等信息 (如果解析到了且原本没有)
                if meta.get('cover') and not song.cover:
                    song.cover = meta.get('cover')
            else:
                print(f"    -> Could not resolve correct artist from metadata/filename.")

        await db.commit()
        print("Healing complete.")

if __name__ == "__main__":
    asyncio.run(heal_unknown_data())
