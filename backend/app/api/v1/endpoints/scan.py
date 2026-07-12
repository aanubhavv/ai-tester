import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas.scan import ScanRequest, ScanResponse
from app.services.browser_service import BrowserService, ScanError
from app.services.page_readiness import ReadinessConfig
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/scan", response_model=ScanResponse)
def scan_website(request: ScanRequest):
    """
    Scan a website and return page information with a screenshot.

    This endpoint is intentionally thin — its only job is to:
    1. Receive the validated request (Pydantic already checked the URL)
    2. Delegate to BrowserService for all browser work
    3. Return the result or a clean error

    Error handling strategy:
    - ScanError (from BrowserService) → 502 with descriptive message.
      502 (Bad Gateway) is semantically correct: the scanner acts as a
      gateway to the target website, and the error occurred while trying
      to reach or process the upstream page.
      Previously this was 422 (Unprocessable Entity), which is reserved
      for request validation errors (e.g., malformed URL in request body).
    - Everything else → Falls through to the global exception handler (500)
    """
    try:
        # Build readiness config from environment settings.
        # The full ReadinessConfig has many options with sensible defaults;
        # we only override the values exposed in Settings for .env tuning.
        readiness_config = ReadinessConfig(
            max_wait_seconds=settings.readiness_max_wait_seconds,
            final_delay_seconds=settings.readiness_final_delay_seconds,
            wait_for_videos=settings.readiness_wait_for_videos,
            videos_timeout_ms=settings.readiness_videos_timeout_ms,
            navigation_wait_strategy=settings.readiness_navigation_wait_strategy,
            enable_scroll_discovery=settings.readiness_enable_scroll_discovery,
            scroll_step_pixels=settings.readiness_scroll_step_pixels,
            scroll_pause_ms=settings.readiness_scroll_pause_ms,
            max_scroll_iterations=settings.readiness_max_scroll_iterations,
        )

        service = BrowserService(screenshots_dir=settings.screenshots_dir)
        result = service.scan_url(str(request.url), readiness_config=readiness_config)
        return ScanResponse(**result)

    except ScanError as exc:
        logger.warning(f"Scan failed for {request.url}: {exc}")
        return JSONResponse(
            status_code=502,
            content={
                "success": False,
                "detail": str(exc),
            },
        )
