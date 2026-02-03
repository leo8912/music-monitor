
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from core.database import AsyncSessionLocal
from app.models.song import Song
from app.services.enrichment_service import EnrichmentService

async def verify_backoff():
    async with AsyncSessionLocal() as db:
        # 1. 找到一个需要补全的歌曲
        stmt = select(Song).limit(1)
        result = await db.execute(stmt)
        song = result.scalar_one_or_none()
        
        if not song:
            print("No songs found to test.")
            return
            
        service = EnrichmentService()
        
        print(f"Testing song: {song.title}")
        print(f"  Initial last_enrich_at: {song.last_enrich_at}")
        
        # 2. 第一次尝试补全 (应该会触发)
        print("Running first enrichment...")
        await service.enrich_song(song.id)
        
        # 重新加载数据
        await db.refresh(song)
        print(f"  After first attempt: {song.last_enrich_at}")
        
        # 3. 验证 _needs_enrichment
        needs = service._needs_enrichment(song)
        print(f"  _needs_enrichment (immediately after): {needs}")
        
        if needs:
            print("FAILED: Backoff did not trigger!")
        else:
            print("SUCCESS: Backoff is working!")

if __name__ == "__main__":
    asyncio.run(verify_backoff())
