import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

import logging
from logging.handlers import TimedRotatingFileHandler

# Configure logging to match main.py
LOG_FILE = "logs/application.log"
os.makedirs("logs", exist_ok=True)
file_handler = TimedRotatingFileHandler(
    LOG_FILE, 
    when='midnight', 
    interval=1, 
    backupCount=10, 
    encoding='utf-8'
)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        file_handler
    ]
)

from core.database import AsyncSessionLocal
from app.services.library import LibraryService

async def trigger_refresh():
    async with AsyncSessionLocal() as db:
        print("--- 正在触发 '宿羽阳' 的深度刷新 (含元数据治愈) ---")
        lib_service = LibraryService()
        await lib_service.refresh_artist(db, "宿羽阳")
        await db.commit()
        print("\n--- 刷新完成! ---")

if __name__ == "__main__":
    asyncio.run(trigger_refresh())
