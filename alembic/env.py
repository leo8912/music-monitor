import asyncio
from logging.config import fileConfig
import sys
import os

# 将当前目录加入 path 以便导入 app
sys.path.insert(0, os.getcwd())

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from app.models.base import Base  # Import app models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# [Fix] Force Alembic to use the application's configured DATABASE_URL
# This ensures it respects Docker ENV vars and ConfigManager overrides
from core.config_manager import get_config_manager
from core.database import DATABASE_URL, sync_database_url

# Reload config to ensure we pick up the 'config/' subdirectory DB path if present
get_config_manager().reload()

config.set_main_option("sqlalchemy.url", DATABASE_URL)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = DATABASE_URL
    import sys
    print(f"DEBUG: Alembic using DATABASE_URL: {DATABASE_URL}", file=sys.stderr)
    
    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
