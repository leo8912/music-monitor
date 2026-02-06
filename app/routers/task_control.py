from fastapi import APIRouter, HTTPException
from app.services.task_monitor import task_monitor

router = APIRouter(prefix="/api/tasks", tags=["Task Control"])

@router.post("/{task_id}/pause")
async def pause_task(task_id: str):
    await task_monitor.pause_task(task_id)
    return {"status": "paused", "task_id": task_id}

@router.post("/{task_id}/resume")
async def resume_task(task_id: str):
    await task_monitor.resume_task(task_id)
    return {"status": "resumed", "task_id": task_id}

@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    await task_monitor.cancel_task(task_id)
    return {"status": "cancelled", "task_id": task_id}
