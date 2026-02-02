# -*- coding: utf-8 -*-
"""
简化调度器 - APScheduler 封装

提供任务调度功能的简单封装。

Author: google
Created: 2026-01-26
"""
import logging
from typing import Optional, Callable, List
from datetime import datetime

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False
    AsyncIOScheduler = None

logger = logging.getLogger(__name__)


class DummyScheduler:
    """当 APScheduler 不可用时的占位调度器"""
    
    def start(self):
        logger.warning("APScheduler 未安装，调度功能不可用")
    
    def shutdown(self, wait: bool = True):
        pass
    
    def add_job(self, func, trigger=None, **kwargs):
        pass
    
    def get_jobs(self) -> List:
        return []
    
    def get_job(self, job_id: str):
        return None
    
    def modify_job(self, job_id: str, **kwargs):
        pass
    
    def remove_job(self, job_id: str):
        pass


class SimpleScheduler:
    """简化的调度器封装"""
    
    def __init__(self):
        if HAS_APSCHEDULER:
            self._scheduler = AsyncIOScheduler()
        else:
            self._scheduler = DummyScheduler()
        self._started = False
    
    def start(self):
        """启动调度器"""
        if not self._started:
            try:
                self._scheduler.start()
                self._started = True
                logger.info("调度器已启动")
            except Exception as e:
                logger.error(f"调度器启动失败: {e}")
    
    def shutdown(self, wait: bool = True):
        """关闭调度器"""
        if self._started:
            try:
                self._scheduler.shutdown(wait=wait)
                self._started = False
                logger.info("调度器已关闭")
            except Exception as e:
                logger.error(f"调度器关闭失败: {e}")
    
    def add_job(self, func: Callable, trigger=None, id: str = None, **kwargs):
        """添加定时任务"""
        return self._scheduler.add_job(func, trigger=trigger, id=id, **kwargs)
    
    def get_jobs(self) -> List:
        """获取所有任务"""
        return self._scheduler.get_jobs()
    
    def get_job(self, job_id: str):
        """获取指定任务"""
        return self._scheduler.get_job(job_id)
    
    def modify_job(self, job_id: str, **kwargs):
        """修改任务"""
        return self._scheduler.modify_job(job_id, **kwargs)
    
    def remove_job(self, job_id: str):
        """移除任务"""
        return self._scheduler.remove_job(job_id)


# 全局调度器实例
scheduler = SimpleScheduler()
