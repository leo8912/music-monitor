from abc import ABC, abstractmethod
from typing import List
from domain.models import MediaInfo

class MonitorPlugin(ABC):
    """Base class for all music/video monitor plugins."""
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the source name (e.g., 'netease', 'bilibili')"""
        pass

    @abstractmethod
    async def get_new_content(self, user_id: str, user_name: str = "") -> List[MediaInfo]:
        """
        Fetch new content for a specific user ID.
        
        Args:
            user_id: The ID of the artist/uploader to monitor.
            user_name: Friendly name for logging.
            
        Returns:
            A list of MediaInfo objects found.
        """
        pass
    
    async def start(self):
        """Optional initialization hook."""
        pass

    async def stop(self):
        """Optional clean-up hook."""
        pass
