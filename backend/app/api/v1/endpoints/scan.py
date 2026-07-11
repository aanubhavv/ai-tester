import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas.scan import ScanRequest, ScanResponse
from app.services.browser_service import BrowserService, ScanError
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
    - ScanError (from BrowserService) → 422 with descriptive message
    - Everything else → Falls through to the global exception handler (500)
    """
    try:
        service = BrowserService(screenshots_dir=settings.screenshots_dir)
        result = service.scan_url(str(request.url))
        return ScanResponse(**result)

    except ScanError as exc:
        logger.warning(f"Scan failed for {request.url}: {exc}")
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "detail": str(exc),
            },
        )
