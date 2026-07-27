"""
browser_stream.py
WebSocket endpoint: /ws/browser/{job_id}

Clients connect here to receive a live stream of browser screenshot frames
while a Playwright test is executing on the server.
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request

from app.services.playwright_execution.browser_stream_manager import browser_stream_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/browser/{job_id}")
async def browser_stream_ws(job_id: str, websocket: WebSocket):
    """
    WebSocket endpoint that streams live browser screenshots for a running test job.

    Frame protocol (JSON):
      {"type": "screenshot", "data": "<base64 png>"}
      {"type": "log",        "text": "..."}
      {"type": "status",     "value": "running" | "passed" | "failed" | "timeout"}
      {"type": "error",      "message": "..."}
      {"type": "done",       "result": {...}}
      {"type": "ping"}        — keepalive, no response needed
    """
    await browser_stream_manager.connect(job_id, websocket)
    logger.info(f"[BrowserStreamWS] Client connected for job: {job_id}")

    try:
        await browser_stream_manager.stream_to_client(job_id, websocket)
    except WebSocketDisconnect:
        logger.info(f"[BrowserStreamWS] Client disconnected: {job_id}")
    except Exception as e:
        logger.error(f"[BrowserStreamWS] Error for job {job_id}: {e}")
    finally:
        browser_stream_manager.disconnect(job_id, websocket)
        logger.info(f"[BrowserStreamWS] Session closed for job: {job_id}")

@router.post("/api/v1/browser-stream/{job_id}/frame")
async def receive_browser_frame(job_id: str, request: Request):
    """
    Receives a base64 encoded JPEG frame from the executing Node Playwright test
    and pushes it to the browser stream manager queue.
    """
    try:
        body = await request.body()
        frame_data = body.decode('utf-8')
        if frame_data:
            await browser_stream_manager.put_frame(job_id, {
                "type": "screenshot",
                "data": frame_data,
                "mime": "image/jpeg"
            })
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error receiving frame for {job_id}: {e}")
        return {"status": "error", "message": str(e)}
