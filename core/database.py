"""
Database核心配置 - 数据库连接和模型定义

此文件负责：
- 数据库连接配置和引擎初始化
- 同步和异步数据库会话管理
- 数据库模型定义（MediaRecord）
- 数据库初始化和迁移
- 数据库会话依赖注入

Author: music-monitor development team

更新日志:
2026-01-21 - 修复了异步引擎与同步调用混用导致的MissingGreenlet错误
           重构了数据库初始化逻辑，实现了async_init_db和async_migrate_db函数
           添加了线程池执行异步数据库初始化，避免循环冲突
2026-01-21 - 修改了Base导入，使用统一模型定义，确保所有模型都能正确创建
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Index, Text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Use a local SQLite database by default
# Use async SQLite driver
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///config/music_monitor.db")

# Import unified Base from app.models to include all models
# Import unified Base from app.models.base to avoid circular dependency
# (do NOT import from app.models as it imports all models)
from app.models.base import Base

# Create async engine
async_engine = create_async_engine(DATABASE_URL, echo=False)  # [Fix] Enable echo for debugging flicker issue
AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


# Database initialization for async
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from alembic.config import Config
from alembic import command

async def async_run_migrations():
    """Run Alembic migrations programmatically."""
    def run_upgrade():
        import os
        # Ensure we are in the project root
        project_root = os.path.dirname(os.path.dirname(__file__)) # d:/code/music-monitor
        alembic_ini_path = os.path.join(project_root, "alembic.ini")
        alembic_cfg = Config(alembic_ini_path)
        # Force the Alembic Config to use the runtime DATABASE_URL
        # This ensures env.py receives the correct URL regardless of alembic.ini
        # We must use a sync URL for the config object if we were running offline,
        # but env.py converts it to async engine anyway.
        alembic_cfg.set_main_option("sqlalchemy.url", str(DATABASE_URL))
        
        command.upgrade(alembic_cfg, "head")

    # Alembic is sync, so run in thread
    await asyncio.to_thread(run_upgrade)

async def async_init_db():
    import logging
    logger = logging.getLogger("core.database")
    logger.info(f"DEBUG: Initializing Database with URL: {DATABASE_URL}")
    
    async with async_engine.begin() as conn:
        # Create all tables (including tracking existing ones)
        await conn.run_sync(Base.metadata.create_all)
        
    # Run Alembic Upgrade
    try:
        await async_run_migrations()
        logger.info("Database migrations completed successfully.")
    except Exception as e:
        logger.error(f"Database migration failed: {e}")

# Create sync engine for backward compatibility where needed
sync_database_url = DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite://")
if "://" in sync_database_url and sync_database_url != DATABASE_URL:
    from sqlalchemy import create_engine
    sync_engine = create_engine(sync_database_url, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
else:
    # Fallback for non-async URLs or when replacement didn't work
    from sqlalchemy import create_engine
    # Create a sync engine from the async URL by replacing the driver
    sync_url = DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite://")
    if sync_url == DATABASE_URL:  # if no replacement happened, try another pattern
        sync_url = DATABASE_URL.replace("aiosqlite", "pysqlite")
    sync_engine = create_engine(sync_url, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

def init_db():
    # For sync usage, we'll use an async wrapper
    # This is a workaround for the mixed sync/async usage in the app
    import threading
    import concurrent.futures
    
    def run_async_init():
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(async_init_db())
        finally:
            loop.close()
    
    # Run in a separate thread to avoid loop conflicts
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async_init)
            future.result()
    except Exception as e:
        print(f"Database initialization failed: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_session():
    async with AsyncSessionLocal() as session:
        yield session
