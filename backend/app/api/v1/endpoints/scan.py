import logging
from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.schemas.scan import ScanOptions, ScanResponse
from app.schemas.report import ScanReportSchema, ScanInfoSchema, VersionInfoSchema
from app.services.browser_service import BrowserService, ScanError
from app.services.artifact_service import ArtifactService
from app.services.scan_logger import ScanLogCollector
from app.services.page_readiness import ReadinessConfig
from app.models.scan_models import generate_scan_id, ScanStatus
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


def _build_report(
    scan_id: str,
    url: str,
    started_at: str,
    completed_at: str,
    duration_seconds: float,
    browser_mode: str,
    status: str,
    result: dict,
    app_version: str,
) -> dict:
    """
    Build the master report dict from a scan result.

    This is a helper function that constructs the ScanReportSchema
    from the raw BrowserService result dict. It's a function (not a method)
    because report construction is a pure transformation — it doesn't
    need access to any service instance.

    Returns:
        A dict suitable for json.dump() and for ScanReportSchema validation.
    """
    report = ScanReportSchema(
        scan_info=ScanInfoSchema(
            scan_id=scan_id,
            url=url,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            browser_mode=browser_mode,
            status=status,
        ),
        analysis=result["analysis"],
        readiness=result.get("readiness"),
        versions=VersionInfoSchema(
            qaforge_version=app_version,
            playwright_version=result.get("playwright_version", "unknown"),
            browser_version=result.get("browser_version", "unknown"),
        ),
        warnings=result.get("warnings", []),
        scan_quality_score=result.get("scan_quality_score", 1.0),
    )
    return report.model_dump(mode="json")


@router.post("/scan", response_model=ScanResponse)
def scan_website(
    request: Request,
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
    Scan a website, persist artifacts, and return scan results.

    This endpoint orchestrates the full scan lifecycle:
    1. Validate the URL query parameter
    2. Generate a unique scan ID
    3. Build a ScanOptions object from the query params
    4. Delegate to BrowserService for all browser work
    5. Persist artifacts via ArtifactService (screenshot, analysis, report, log)
    6. Return the result with scan_id for future retrieval

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

    # --- Generate scan identity ---
    scan_id = generate_scan_id()
    scan_log = ScanLogCollector()
    artifact_service = ArtifactService(artifacts_dir=settings.artifacts_dir)
    started_at = datetime.now().isoformat()

    # --- Build per-request options ---
    # ScanOptions bundles all per-request caller choices.
    # Future params (viewport, locale, proxy, etc.) get added here
    # without changing the BrowserService signature.
    options = ScanOptions(
        url=url,
        headless=not headed,
    )

    scan_log.add(f"Scan started: {url}")
    scan_log.add(f"Scan ID: {scan_id}")
    scan_log.add(f"Browser mode: {options.browser_mode}")

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

        scan_log.add("Browser launching...")
        service = BrowserService()
        result = service.scan_url(options, readiness_config=readiness_config)
        scan_log.add("Browser scan completed")

        # --- Persist artifacts ---
        completed_at = datetime.now().isoformat()
        duration_seconds = result["load_time"]

        scan_log.add("Creating artifact directory...")
        artifact_service.create_scan_directory(scan_id)

        # Save screenshot
        scan_log.add("Saving screenshot...")
        artifact_service.save_screenshot(scan_id, result["screenshot_bytes"])

        # Save individual analysis artifacts.
        # result["analysis"] is a Pydantic AnalysisResponse — convert to dict
        # for individual file writes.
        analysis_dict = result["analysis"].model_dump(mode="json")
        readiness_dict = result.get("readiness")
        scan_log.add("Saving analysis artifacts...")
        artifact_service.save_analysis_artifacts(scan_id, analysis_dict, readiness_dict)

        # Build and save the master report
        app_version = request.app.version
        report = _build_report(
            scan_id=scan_id,
            url=url,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            browser_mode=options.browser_mode,
            status=ScanStatus.COMPLETED.value,
            result=result,
            app_version=app_version,
        )
        scan_log.add("Saving master report...")
        artifact_service.save_report(scan_id, report)

        # Save scan log (last, since we want to capture all events)
        scan_log.add("Scan completed successfully")
        artifact_service.save_scan_log(scan_id, scan_log.to_serializable())

        logger.info(f"Scan artifacts saved for {scan_id}")

        # Build screenshot URL for the response
        screenshot_url = f"{settings.api_prefix}/scans/{scan_id}/screenshot"

        return ScanResponse(
            scan_id=scan_id,
            success=True,
            browser_mode=options.browser_mode,
            title=result["title"],
            final_url=result["final_url"],
            status=result["status"],
            load_time=result["load_time"],
            screenshot_url=screenshot_url,
            analysis=result["analysis"],
            warnings=result.get("warnings", []),
            scan_quality_score=result.get("scan_quality_score", 1.0),
            readiness=result.get("readiness"),
        )

    except ScanError as exc:
        logger.warning(f"Scan failed for {url}: {exc}")

        # Persist what we can for failed scans — the log is valuable
        # for debugging why the scan failed.
        scan_log.add(f"Scan failed: {exc}")
        try:
            artifact_service.create_scan_directory(scan_id)
            failed_report = {
                "scan_info": {
                    "scan_id": scan_id,
                    "url": url,
                    "started_at": started_at,
                    "completed_at": datetime.now().isoformat(),
                    "duration_seconds": 0,
                    "browser_mode": options.browser_mode,
                    "status": ScanStatus.FAILED.value,
                },
                "error": str(exc),
            }
            artifact_service.save_report(scan_id, failed_report)
            artifact_service.save_scan_log(scan_id, scan_log.to_serializable())
        except Exception as persist_exc:
            logger.error(f"Failed to persist failed scan artifacts: {persist_exc}")

        return JSONResponse(
            status_code=502,
            content={
                "success": False,
                "scan_id": scan_id,
                "detail": str(exc),
            },
        )

