from fastapi import APIRouter, Depends
from app.services.task_monitor import task_monitor
from app.dependencies import require_auth
from app.schemas import TaskControlResponse

router = APIRouter(prefix="/api/tasks", tags=["Task Control"], dependencies=[Depends(require_auth)])

@router.post("/{task_id}/pause", response_model=TaskControlResponse)
async def pause_task(task_id: str):
    await task_monitor.pause_task(task_id)
    return {"status": "paused", "task_id": task_id}

@router.post("/{task_id}/resume", response_model=TaskControlResponse)
async def resume_task(task_id: str):
    await task_monitor.resume_task(task_id)
    return {"status": "resumed", "task_id": task_id}

@router.post("/{task_id}/cancel", response_model=TaskControlResponse)
async def cancel_task(task_id: str):
    # arq 模式: cancel 标志写入 Redis, worker 进程内 check_status 会
    # 感知并抛出 TaskCancelledException; inline 模式由内存标志驱动。
    await task_monitor.cancel_task(task_id)
    return {"status": "cancelled", "task_id": task_id}
