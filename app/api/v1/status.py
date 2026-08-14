# -*- coding: utf-8 -*-
"""
系统状态路由 - 服务运行状态查询

从 system.py 拆出（阶段 4.6）：状态域单一职责。

Author: google
Updated: 2026-08-13
"""
import logging

from fastapi import APIRouter, Depends

from app.schemas import SystemStatusResponse
from core.scheduler import scheduler
from app.dependencies import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])
logger = logging.getLogger(__name__)


@router.get("/api/status", response_model=SystemStatusResponse)
async def get_status():
    jobs = scheduler.get_jobs()
    job_info = [{"id": j.id, "next_run": j.next_run_time.isoformat() if j.next_run_time else None} for j in jobs]
    return {"status": "running", "jobs": job_info}
