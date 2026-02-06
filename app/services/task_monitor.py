import logging
import uuid
import time
from typing import Dict, Optional, Any
from core.websocket import manager

logger = logging.getLogger(__name__)

class TaskMonitor:
    """
    Global Task Monitor Service
    
    Manages the lifecycle of background tasks and broadcasts updates via WebSocket.
    Singleton pattern usage recommended.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskMonitor, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.tasks = {}
        self._pause_events = {}  # task_id -> asyncio.Event
        self._cancel_flags = set() # task_id set
        
        self._initialized = True

    async def start_task(
        self, 
        task_type: str, 
        message: str = "Starting...", 
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new task and broadcast pending state.
        Returns: task_id (str)
        """
        import asyncio
        task_id = str(uuid.uuid4())
        timestamp = int(time.time() * 1000)
        
        task_data = {
            "taskId": task_id,
            "taskType": task_type,
            "state": "running",
            "progress": 0,
            "message": message,
            "details": details or {},
            "timestamp": timestamp
        }
        
        self.tasks[task_id] = task_data
        
        # Initialize control primitives
        self._pause_events[task_id] = asyncio.Event()
        self._pause_events[task_id].set() # Initially running (not paused)
        
        await self._broadcast(task_data)
        logger.info(f"Task Started [{task_type}]: {message} (ID: {task_id})")
        return task_id

    async def update_progress(
        self, 
        task_id: str, 
        progress: int, 
        message: Optional[str] = None, 
        details: Optional[Dict[str, Any]] = None,
        state: str = "running"
    ):
        """
        Update task progress and broadcast.
        """
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        task["progress"] = progress
        if message:
            task["message"] = message
        if details:
            if "details" not in task:
                task["details"] = {}
            task["details"].update(details)
        
        # Don't overwrite state if it's already 'paused' or 'cancelling' unless explicitly finishing
        current_state = task.get("state", "running")
        if state == "running" and current_state in ["paused", "cancelling"]:
             pass # Keep current specific state
        else:
             task["state"] = state
             
        task["timestamp"] = int(time.time() * 1000)
        
        await self._broadcast(task)

    async def finish_task(self, task_id: str, message: str = "Completed", details: Optional[Dict] = None):
        """
        Mark task as completed and broadcast.
        """
        await self.update_progress(task_id, 100, message, details, state="completed")
        self._cleanup_task(task_id)
        logger.info(f"Task Completed (ID: {task_id})")

    async def error_task(self, task_id: str, error_message: str):
        """
        Mark task as error and broadcast.
        """
        await self.update_progress(task_id, self.tasks.get(task_id, {}).get("progress", 0), error_message, state="error")
        self._cleanup_task(task_id)
        logger.error(f"Task Failed (ID: {task_id}): {error_message}")

    # --- Control Methods ---

    async def pause_task(self, task_id: str):
        if task_id in self._pause_events:
            self._pause_events[task_id].clear() # Will block wait()
            await self.update_progress(task_id, self._get_progress(task_id), state="paused")
            logger.info(f"Task Paused: {task_id}")

    async def resume_task(self, task_id: str):
         if task_id in self._pause_events:
            self._pause_events[task_id].set() # Unblock
            await self.update_progress(task_id, self._get_progress(task_id), state="running")
            logger.info(f"Task Resumed: {task_id}")

    async def cancel_task(self, task_id: str):
        if task_id in self.tasks:
            self._cancel_flags.add(task_id)
            # Ensure not paused so it can wake up and cancel
            if task_id in self._pause_events:
                self._pause_events[task_id].set()
            
            await self.update_progress(task_id, self._get_progress(task_id), state="cancelling")
            logger.info(f"Task Cancellation Requested: {task_id}")

    async def check_status(self, task_id: str):
        """
        Called by worker loops. 
        1. Checks if cancelled -> Raises TaskCancelledException
        2. Checks if paused -> Waits until resumed
        """
        if not task_id:
            return

        # Check cancellation
        if task_id in self._cancel_flags:
            raise TaskCancelledException(f"Task {task_id} cancelled by user")
            
        # Check pause (Wait if cleared)
        if task_id in self._pause_events:
            await self._pause_events[task_id].wait()

    def _cleanup_task(self, task_id: str):
        if task_id in self._pause_events:
            del self._pause_events[task_id]
        if task_id in self._cancel_flags:
            self._cancel_flags.remove(task_id)

    def _get_progress(self, task_id: str) -> int:
        return self.tasks.get(task_id, {}).get("progress", 0)

    async def _broadcast(self, task_data: Dict):
        """
        Construct WS message and send.
        """
        msg = {
            "type": "task_progress",
            "data": task_data
        }
        await manager.broadcast(msg)

class TaskCancelledException(Exception):
    pass

# Global Instance
task_monitor = TaskMonitor()
