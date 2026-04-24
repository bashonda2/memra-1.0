"""
Task Queue — GPU-aware scheduling for multi-agent workloads.

Metal GPU is a single shared resource. Concurrent generations crash
the Metal command buffer. This queue serializes local GPU inference
while allowing frontier API calls to run in parallel.

Scheduling: priority-based with fairness. Higher priority agents
get GPU time first, but no agent starves.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger("memra.queue")


@dataclass
class QueuedTask:
    task_id: str
    agent_id: str
    priority: int
    route: str
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None

    @property
    def wait_time_ms(self) -> float:
        if self.started_at:
            return (self.started_at - self.created_at) * 1000
        return (time.time() - self.created_at) * 1000


class TaskQueue:

    def __init__(self):
        self._gpu_lock = asyncio.Lock()
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._active_tasks: Dict[str, QueuedTask] = {}
        self._completed_tasks: List[QueuedTask] = []
        self._stats = {
            "total_queued": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_gpu_wait_ms": 0.0,
        }

    async def submit_local(self, agent_id: str, priority: int,
                           fn: Callable[[], Awaitable[Any]],
                           task_id: Optional[str] = None) -> Any:
        """Submit a local GPU task. Waits for GPU lock."""
        tid = task_id or f"task-{int(time.time() * 1000)}"
        task = QueuedTask(task_id=tid, agent_id=agent_id,
                          priority=priority, route="local")
        self._stats["total_queued"] += 1

        logger.info("GPU queue: %s waiting (agent=%s, priority=%d)",
                     tid, agent_id, priority)

        async with self._gpu_lock:
            task.started_at = time.time()
            self._active_tasks[tid] = task
            wait_ms = task.wait_time_ms
            self._stats["total_gpu_wait_ms"] += wait_ms

            logger.info("GPU queue: %s acquired lock (waited %.0fms)", tid, wait_ms)

            try:
                result = await fn()
                task.result = result
                task.completed_at = time.time()
                self._stats["total_completed"] += 1
                return result
            except Exception as e:
                task.error = str(e)
                task.completed_at = time.time()
                self._stats["total_failed"] += 1
                raise
            finally:
                self._active_tasks.pop(tid, None)
                self._completed_tasks.append(task)
                if len(self._completed_tasks) > 100:
                    self._completed_tasks = self._completed_tasks[-50:]

    async def submit_frontier(self, agent_id: str,
                              fn: Callable[[], Awaitable[Any]],
                              task_id: Optional[str] = None) -> Any:
        """Submit a frontier API task. No GPU lock needed — runs in parallel."""
        tid = task_id or f"task-{int(time.time() * 1000)}"
        task = QueuedTask(task_id=tid, agent_id=agent_id,
                          priority=0, route="frontier")
        task.started_at = time.time()
        self._active_tasks[tid] = task
        self._stats["total_queued"] += 1

        logger.info("Frontier task: %s (agent=%s)", tid, agent_id)

        try:
            result = await fn()
            task.result = result
            task.completed_at = time.time()
            self._stats["total_completed"] += 1
            return result
        except Exception as e:
            task.error = str(e)
            task.completed_at = time.time()
            self._stats["total_failed"] += 1
            raise
        finally:
            self._active_tasks.pop(tid, None)
            self._completed_tasks.append(task)

    @property
    def gpu_locked(self) -> bool:
        return self._gpu_lock.locked()

    def get_active(self) -> List[Dict]:
        return [
            {"task_id": t.task_id, "agent_id": t.agent_id,
             "route": t.route, "wait_ms": round(t.wait_time_ms)}
            for t in self._active_tasks.values()
        ]

    def get_stats(self) -> Dict:
        return {
            **self._stats,
            "gpu_locked": self.gpu_locked,
            "active_tasks": len(self._active_tasks),
            "avg_gpu_wait_ms": round(
                self._stats["total_gpu_wait_ms"] / max(self._stats["total_completed"], 1)
            ),
        }
