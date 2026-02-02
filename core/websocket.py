import logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WS Connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WS Disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            logger.info(f"No active WS connections (skip broadcast): {message.get('message', 'Unknown')}")
            return
            
        logger.debug(f"Broadcasting to {len(self.active_connections)} clients: {message.get('message', '')}")
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass
    
    async def disconnect_all(self):
        """关闭所有活动连接"""
        for connection in self.active_connections[:]:  # 创建副本以避免在迭代时修改列表
            try:
                await connection.close()
            except:
                pass  # 连接可能已经关闭
        self.active_connections.clear()

manager = ConnectionManager()
