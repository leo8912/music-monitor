from typing import List, Optional
from datetime import datetime
import logging
from bilibili_api import user
from domain.models import MediaInfo, MediaType
from plugins.base import MonitorPlugin

logger = logging.getLogger(__name__)

from bilibili_api import search

class BilibiliSearcher:
    """Helper to search for videos on Bilibili."""
    
    async def search_video(self, keyword: str) -> Optional[str]:
        """
        Search for a video and return the URL of the first result.
        """
        logger.info(f"正在 B 站搜索: {keyword}")
        try:
            # search_by_type returns simplified result structure
            res = await search.search_by_type(keyword, search_type=search.SearchObjectType.VIDEO, page=1)
            
            # The structure of 'res' depends on bilibili-api version.
            # Usually: res['result'] is a list of items.
            items = res.get('result', [])
            if items:
                first = items[0]
                # Log the found title for debugging
                title = first.get('title', 'Unknown Title').replace('<em class="keyword">', '').replace('</em>', '')
                logger.info(f"B 站搜索命中: [{title}] ({first.get('bvid')})")
                
                # Prefer BVID for consistent ID extraction
                if first.get('bvid'):
                    return f"https://www.bilibili.com/video/{first.get('bvid')}"
                return first.get('arcurl')
                
        except Exception as e:
            logger.error(f"B 站搜索出错: {e}")
            
        return None

# Deprecated or unused if we only use it for search
class BilibiliMonitor(MonitorPlugin):
    @property
    def source_name(self) -> str:
        return "bilibili"

    async def get_new_content(self, user_id: str, user_name: str = "") -> List[MediaInfo]:
        return [] # Disable monitoring for now logic changed
