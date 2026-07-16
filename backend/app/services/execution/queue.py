import asyncio
import logging
from typing import Callable, Coroutine, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Job:
    id: str
    type: str # "generate" or "execute"
    coro: Coroutine[Any, Any, Any]

class ExecutionQueue:
    """
    A simple in-memory job queue for background processing of 
    test case generation and execution jobs.
    """
    def __init__(self):
        self._queue = asyncio.Queue()
        self._worker_task = None

    async def start(self):
        if not self._worker_task:
            self._worker_task = asyncio.create_task(self._worker())
            logger.info("ExecutionQueue worker started.")

    async def stop(self):
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            logger.info("ExecutionQueue worker stopped.")

    def enqueue(self, job_id: str, job_type: str, coro: Coroutine[Any, Any, Any]):
        job = Job(id=job_id, type=job_type, coro=coro)
        self._queue.put_nowait(job)
        logger.info(f"Enqueued {job_type} job: {job_id}")

    async def _worker(self):
        while True:
            job = await self._queue.get()
            logger.info(f"Starting {job.type} job: {job.id}")
            try:
                await job.coro
                logger.info(f"Finished {job.type} job: {job.id}")
            except Exception as e:
                logger.error(f"Error in {job.type} job {job.id}: {e}", exc_info=True)
            finally:
                self._queue.task_done()

# Global singleton
execution_queue = ExecutionQueue()
