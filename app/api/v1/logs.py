# -*- coding: utf-8 -*-
"""
系统日志路由 - 应用日志查询

从 system.py 拆出（阶段 4.6）：日志域单一职责。
注意：R9 已知问题，api_log_handler.get_recent_logs 方法缺失，
当前端点保持原样，后续阶段修复。

Author: google
Updated: 2026-08-13
"""
import logging

from fastapi import APIRouter, Depends

from core.logger import api_log_handler
from app.dependencies import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])
logger = logging.getLogger(__name__)


@router.get("/api/logs")
async def get_logs():
    """Get recent logs."""
    return api_log_handler.get_recent_logs()
