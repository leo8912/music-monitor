from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime
from app.models.base import Base

class WeChatSession(Base):
    __tablename__ = "wechat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    session_data = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    expires_at = Column(DateTime, nullable=False)

    def __repr__(self):
        return f"<WeChatSession(user_id={self.user_id}, expires_at={self.expires_at})>"
