import logging
from urllib.parse import urlparse

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.schemas.scan import ScanOptions, ScanResponse
from app.services.browser_service import BrowserService, ScanError
from app.services.page_readiness import ReadinessConfig
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _validate_url(url: str) -> str | None:
    """
    Validate that a URL is well-formed and has a supported scheme.

    Returns None if valid, or an error message string if invalid.

    Why a standalone function instead of Pydantic's HttpUrl?
    We moved from a JSON body (where Pydantic validates automatically)
    to query params (where FastAPI gives us a raw string). This function
    provides equivalent validation without pulling in Pydantic's URL
    type for a single check.

    Why not in BrowserService?
    BrowserService trusts its callers — it's an internal service, not
    an API boundary. Validation belongs at the edge (the endpoint).
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return "URL could not be parsed."

    if not parsed.scheme:
        return "URL must include a scheme (e.g., https://example.com)."

    if parsed.scheme not in ("http", "https"):
        return f"Unsupported URL scheme '{parsed.scheme}'. Use http or https."

    if not parsed.netloc:
        return "URL must include a domain (e.g., https://example.com)."

    return None


@router.post("/scan", response_model=ScanResponse)
def scan_website(
    url: str = Query(
        ...,
        description="The target URL to scan. Must include scheme (https://).",
        examples=["https://example.com"],
    ),
    headed: bool = Query(
        False,
        description=(
            "Browser display mode. "
            "false (default) = headless (invisible). "
            "true = headed (visible browser window)."
        ),
    ),
):
    """
    Scan a website and return page information with a screenshot.

    This endpoint is intentionally thin — its only job is to:
    1. Validate the URL query parameter
    2. Build a ScanOptions object from the query params
    3. Delegate to BrowserService for all browser work
    4. Return the result or a clean error

    Query Parameters:
    - **url**: The target URL to scan (required).
    - **headed**: Whether to show the browser window (optional, default false).

    Error handling strategy:
    - Invalid URL → 422 with descriptive message.
    - ScanError (from BrowserService) → 502 with descriptive message.
      502 (Bad Gateway) is semantically correct: the scanner acts as a
      gateway to the target website, and the error occurred while trying
      to reach or process the upstream page.
    - Everything else → Falls through to the global exception handler (500)
    """
    # --- Validate URL ---
    validation_error = _validate_url(url)
    if validation_error:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "detail": validation_error,
            },
        )

    # --- Build per-request options ---
    # ScanOptions bundles all per-request caller choices.
    # Future params (viewport, locale, proxy, etc.) get added here
    # without changing the BrowserService signature.
    options = ScanOptions(
        url=url,
        headless=not headed,
    )

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
        result = service.scan_url(options, readiness_config=readiness_config)
        return ScanResponse(**result)

    except ScanError as exc:
        logger.warning(f"Scan failed for {url}: {exc}")
        return JSONResponse(
            status_code=502,
            content={
                "success": False,
                "detail": str(exc),
            },
        )
