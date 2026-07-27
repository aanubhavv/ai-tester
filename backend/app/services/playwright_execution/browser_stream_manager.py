"""
browser_stream_manager.py
Manages WebSocket connections and per-job asyncio queues for live browser screenshot streaming.
"""
import asyncio
import logging
from typing import Dict, List, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class BrowserStreamManager:
    """
    Manages per-job asyncio queues and active WebSocket connections.

    Correct execution order:
      1. test_cases._execution_job calls create_job(job_id) — creates queue immediately
         so the frontend WS client can connect and see "Connecting..." right away
      2. create_task(streaming_runner.run(job_id, url)) — mirror browser launches
      3. streaming_runner calls set_ready(job_id) once the page has loaded
      4. test_cases._execution_job awaits wait_ready(job_id) — unblocks when browser is live
      5. execute_script() runs — test and live feed are in sync
      6. execute_script() finishes → stop_streaming(job_id) → streaming runner exits
      7. streaming runner finally: close_job() (sentinel) → cleanup_job()
    """

    def __init__(self):
        # job_id -> set of connected WebSocket objects
        self._connections: Dict[str, List[WebSocket]] = {}
        # ws -> asyncio.Queue of frame dicts
        self._client_queues: Dict[WebSocket, asyncio.Queue] = {}
        # job_id -> list of recent frames (history) for new connections
        self._job_history: Dict[str, List[dict]] = {}
        # job_id -> Event; set when streaming runner has loaded the page and is ready
        self._ready_events: Dict[str, asyncio.Event] = {}
        # job_id -> Event; set when test execution finishes (signals streaming runner to stop)
        self._stop_events: Dict[str, asyncio.Event] = {}

    # ------------------------------------------------------------------
    # Job lifecycle
    # ------------------------------------------------------------------

    def create_job(self, job_id: str):
        """
        Create events for a job.
        Called by test_cases._execution_job BEFORE starting the streaming task,
        so the frontend WS client can connect immediately and see status updates.
        Idempotent.
        """
        if job_id not in self._ready_events:
            self._job_history[job_id] = []
            self._ready_events[job_id] = asyncio.Event()
            self._stop_events[job_id] = asyncio.Event()
            self._connections[job_id] = []
            logger.info(f"[BrowserStream] Created job {job_id}")

    def get_stop_event(self, job_id: str) -> Optional[asyncio.Event]:
        return self._stop_events.get(job_id)

    async def put_frame(self, job_id: str, frame: dict):
        """Push a frame into all queues for connected clients."""
        # Save to history (keep last 50 frames to avoid memory bloat, just enough for initial load)
        if job_id in self._job_history:
            self._job_history[job_id].append(frame)
            if len(self._job_history[job_id]) > 50:
                self._job_history[job_id].pop(0)

        conns = self._connections.get(job_id, [])
        for ws in conns:
            q = self._client_queues.get(ws)
            if q is not None:
                if q.full():
                    try:
                        q.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                try:
                    q.put_nowait(frame)
                except asyncio.QueueFull:
                    pass

    def set_ready(self, job_id: str):
        """
        Called by streaming runner once the mirror browser has navigated and is taking screenshots.
        Unblocks wait_ready() in test_cases._execution_job so the test starts in sync.
        """
        ev = self._ready_events.get(job_id)
        if ev:
            ev.set()
            logger.info(f"[BrowserStream] Browser ready for job {job_id}")

    async def wait_ready(self, job_id: str, timeout: float = 20.0) -> bool:
        """
        Await until the mirror browser has loaded the target page (ready to stream),
        or until timeout. Returns True if ready, False if timed out.
        Called by test_cases._execution_job before starting execute_script().
        """
        ev = self._ready_events.get(job_id)
        if ev is None:
            return False
        try:
            await asyncio.wait_for(ev.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            logger.warning(f"[BrowserStream] wait_ready timed out for job {job_id} after {timeout}s — proceeding with test anyway")
            return False

    def stop_streaming(self, job_id: str):
        """
        Signal the streaming runner to stop capturing frames.
        Called by test_cases._execution_job when execute_script() finishes.
        The streaming runner's finally block handles close_job + cleanup_job.
        """
        ev = self._stop_events.get(job_id)
        if ev:
            ev.set()
            logger.info(f"[BrowserStream] Stop signal sent for job {job_id}")

    def close_job(self, job_id: str):
        """Send None sentinel so stream_to_client() knows streaming has ended."""
        conns = self._connections.get(job_id, [])
        for ws in conns:
            q = self._client_queues.get(ws)
            if q:
                try:
                    q.put_nowait(None)
                except asyncio.QueueFull:
                    try:
                        q.get_nowait()
                        q.put_nowait(None)
                    except Exception:
                        pass

    def cleanup_job(self, job_id: str):
        """Remove all state for this job. Called by streaming runner after close_job()."""
        self._job_history.pop(job_id, None)
        self._ready_events.pop(job_id, None)
        self._stop_events.pop(job_id, None)
        
        conns = self._connections.pop(job_id, [])
        for ws in conns:
            self._client_queues.pop(ws, None)
            
        logger.info(f"[BrowserStream] Cleaned up job {job_id}")

    # ------------------------------------------------------------------
    # WebSocket connection management
    # ------------------------------------------------------------------

    async def connect(self, job_id: str, ws: WebSocket):
        await ws.accept()
        self._connections.setdefault(job_id, []).append(ws)
        self._client_queues[ws] = asyncio.Queue(maxsize=100)
        
        # Catch up with history
        history = self._job_history.get(job_id, [])
        for frame in history:
            try:
                self._client_queues[ws].put_nowait(frame)
            except asyncio.QueueFull:
                pass
                
        logger.info(
            f"[BrowserStream] WS client connected to job {job_id} "
            f"({len(self._connections[job_id])} total)"
        )

    def disconnect(self, job_id: str, ws: WebSocket):
        conns = self._connections.get(job_id, [])
        if ws in conns:
            conns.remove(ws)
        self._client_queues.pop(ws, None)
        logger.info(f"[BrowserStream] WS client disconnected from job {job_id}")

    async def stream_to_client(self, job_id: str, ws: WebSocket):
        """
        Drain the client's queue and forward every frame to this WS client.
        """
        try:
            await ws.send_json({"type": "status", "value": "connecting"})
        except Exception:
            pass

        q = self._client_queues.get(ws)
        if not q:
            return

        try:
            while True:
                try:
                    frame = await asyncio.wait_for(q.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    try:
                        await ws.send_json({"type": "ping"})
                    except Exception:
                        break
                    continue

                if frame is None:
                    # Sentinel — job is done
                    try:
                        await ws.send_json({"type": "done"})
                    except Exception:
                        pass
                    break

                try:
                    await ws.send_json(frame)
                except Exception:
                    break

        except Exception as e:
            logger.warning(f"[BrowserStream] Stream error for job {job_id}: {e}")
        finally:
            self.disconnect(job_id, ws)


# Singleton instance shared across the app
browser_stream_manager = BrowserStreamManager()
