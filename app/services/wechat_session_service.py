# -*- coding: utf-8 -*-
import logging
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import select, delete

from core.database import AsyncSessionLocal
from app.models.wechat_session import WeChatSession

logger = logging.getLogger(__name__)

class WeChatSessionService:
    """企业微信搜索会话服务，处理数据库交互逻辑"""

    @staticmethod
    async def get_db_session(user_id: str) -> Optional[dict]:
        """从数据库获取搜索会话"""
        async with AsyncSessionLocal() as db:
            stmt = select(WeChatSession).where(WeChatSession.user_id == user_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if session and session.expires_at > datetime.now():
                return session.session_data
            
            if session:
                await db.delete(session)
                await db.commit()
        return None

    @staticmethod
    async def set_db_session(user_id: str, data: dict, expire_seconds: int = 300):
        """保存搜索会话到数据库"""
        async with AsyncSessionLocal() as db:
            stmt = select(WeChatSession).where(WeChatSession.user_id == user_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            
            expires_at = datetime.now() + timedelta(seconds=expire_seconds)
            
            if session:
                session.session_data = data
                session.expires_at = expires_at
            else:
                session = WeChatSession(
                    user_id=user_id,
                    session_data=data,
                    expires_at=expires_at
                )
                db.add(session)
            await db.commit()

    @staticmethod
    async def clear_db_session(user_id: str):
        """清除搜索会话"""
        async with AsyncSessionLocal() as db:
            stmt = delete(WeChatSession).where(WeChatSession.user_id == user_id)
            await db.execute(stmt)
            await db.commit()
