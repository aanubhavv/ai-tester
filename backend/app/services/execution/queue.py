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
        self._active_jobs = {}  # job_id -> asyncio.Task
        self._cancelled_jobs = set()  # job_id -> bool

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

    def cancel_job(self, job_id: str):
        self._cancelled_jobs.add(job_id)
        if job_id in self._active_jobs:
            self._active_jobs[job_id].cancel()
            logger.info(f"Sent cancel request to job: {job_id}")

    async def _worker(self):
        while True:
            job = await self._queue.get()
            
            if job.id in self._cancelled_jobs:
                logger.info(f"Skipping cancelled job: {job.id}")
                self._cancelled_jobs.remove(job.id)
                self._queue.task_done()
                continue
                
            logger.info(f"Starting {job.type} job: {job.id}")
            task = asyncio.create_task(job.coro)
            self._active_jobs[job.id] = task
            try:
                await task
                logger.info(f"Finished {job.type} job: {job.id}")
            except asyncio.CancelledError:
                logger.info(f"Job {job.id} was cancelled.")
            except Exception as e:
                logger.error(f"Error in {job.type} job {job.id}: {e}", exc_info=True)
            finally:
                self._active_jobs.pop(job.id, None)
                self._cancelled_jobs.discard(job.id)
                self._queue.task_done()

# Global singleton
execution_queue = ExecutionQueue()
