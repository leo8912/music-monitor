from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class MediaType(Enum):
    SONG = "song"
    ALBUM = "album"
    VIDEO = "video"

@dataclass
class MediaInfo:
    """Standardized media information returned by plugins"""
    id: str  # Unique ID in the source platform
    title: str
    cover_url: str
    url: str  # Link to the content
    publish_time: datetime
    type: MediaType
    author: str  # Singer or Uploader name
    source: str  # "netease", "qqmusic", "bilibili"
    album: Optional[str] = None # Album name
    trial_url: Optional[str] = None  # Bilibili or other free link
    
    def unique_key(self) -> str:
        """Generate a global unique key for deduplication"""
        return f"{self.source}:{self.type.value}:{self.id}"
