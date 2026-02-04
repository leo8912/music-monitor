from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text
from datetime import datetime
from app.models.base import Base

class MediaRecord(Base):
    """
    Stores the history of found media to prevent duplicate notifications.
    """
    __tablename__ = 'media_records'

    id = Column(Integer, primary_key=True)
    unique_key = Column(String, unique=True, index=True, nullable=False) # e.g., "netease:album:123456"
    
    source = Column(String, nullable=False)
    media_type = Column(String, nullable=False)
    media_id = Column(String, nullable=False)
    
    title = Column(String)
    author = Column(String)
    cover = Column(String, nullable=True) # Added for frontend display
    url = Column(String, nullable=True) # Added for playback
    album = Column(String, nullable=True) # Added for better dedup
    publish_time = Column(DateTime)
    
    # Audio & Lyrics extensions
    local_audio_path = Column(String, nullable=True) # Path relative to workspace or absolute
    audio_quality = Column(Integer, nullable=True)   # kbps, e.g. 320, 999
    lyrics = Column(Text, nullable=True)             # LRC content
    lyrics_source = Column(String, nullable=True)
    lyrics_updated_at = Column(DateTime, nullable=True)
    
    # Trial URL for audio previews
    trial_url = Column(String, nullable=True)  # URL for audio preview/trial
    
    found_at = Column(DateTime, default=datetime.now)
    is_pushed = Column(Boolean, default=False)
    push_time = Column(DateTime, nullable=True)
    is_favorite = Column(Boolean, default=False) # Added for user favorites
    extra_sources = Column(Text, nullable=True)  # JSON list of other sources e.g. ["qqmusic", "kugou"]

    def __repr__(self):
        return f"<MediaRecord(key={self.unique_key}, title={self.title})>"
