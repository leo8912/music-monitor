# -*- coding: utf-8 -*-
"""
系统日志路由 - 应用日志查询

从 system.py 拆出（阶段 4.6）：日志域单一职责。

Author: google
Updated: 2026-09-16
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.logger import api_log_handler
from app.dependencies import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])
logger = logging.getLogger(__name__)


class LogsResponse(BaseModel):
    logs: list[Any] = []
    total: int = 0


@router.get("/api/logs", response_model=LogsResponse)
async def get_logs():
    """Get recent logs."""
    data = api_log_handler.get_recent_logs()
    if isinstance(data, list):
        return LogsResponse(logs=data, total=len(data))
    if isinstance(data, dict):
        return LogsResponse(**data)
    return LogsResponse()
