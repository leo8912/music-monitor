"""
Base模型 - 数据库基础配置

此文件定义了SQLAlchemy的基础配置，包括数据库引擎、会话管理器和基础模型类。
提供异步数据库连接支持和基础的数据库会话生成器。

Author: music-monitor development team
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import os

# 使用异步 SQLite 驱动
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///music_monitor.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
