# -*- coding: utf-8 -*-
"""
事件总线 - 简单的事件发布/订阅系统

Author: google
Created: 2026-01-26
"""
import asyncio
import logging
from enum import Enum
from typing import Dict, List, Callable, Any

logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型枚举"""
    NEW_CONTENT = "new_content"
    DOWNLOAD_COMPLETE = "download_complete"
    METADATA_UPDATED = "metadata_updated"
    SCAN_COMPLETE = "scan_complete"


class EventBus:
    """简单的事件总线"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscribers: Dict[EventType, List[Callable]] = {}
        return cls._instance
    
    def subscribe(self, event_type: EventType, callback: Callable):
        """订阅事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug(f"订阅事件: {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, callback: Callable):
        """取消订阅"""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                cb for cb in self._subscribers[event_type] if cb != callback
            ]
    
    async def publish(self, event_type: EventType, data: Any = None):
        """发布事件"""
        if event_type not in self._subscribers:
            return
        
        logger.debug(f"发布事件: {event_type.value}")
        
        for callback in self._subscribers[event_type]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"事件处理错误 {event_type.value}: {e}")


# 全局事件总线实例
_event_bus = EventBus()


def get_event_bus() -> EventBus:
    """获取事件总线实例"""
    return _event_bus
