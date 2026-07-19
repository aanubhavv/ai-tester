import logging
import asyncio
from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.schemas.scan import ScanOptions, ScanRequest, ScanResponse
from app.schemas.report import ScanReportSchema, ScanInfoSchema, VersionInfoSchema
from app.services.browser_service import BrowserService, ScanError
from app.services.artifact_service import ArtifactService
from app.services.scan_logger import ScanLogCollector
from app.services.page_readiness import ReadinessConfig
from app.models.scan_models import ScanStatus
from app.models.execution_models import ExecutionType, ExecutionStatus
from app.schemas.execution import ExecutionCreate
from app.services.execution_service import execution_service
from app.services.project_service import project_service
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _validate_url(url: str) -> str | None:
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
async def scan_website(
    request: Request,
    body: ScanRequest,
):
    validation_error = _validate_url(body.url)
    if validation_error:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "detail": validation_error,
            },
        )

    project_id = body.project_id
    if not project_id:
        project_id = "default_project"
        if not await project_service.get_project(project_id):
            from app.schemas.project import ProjectCreate
            await project_service.create_project(ProjectCreate(name="Default Project", description="Auto-created default project"))

    execution = await execution_service.create_execution(ExecutionCreate(
        project_id=project_id,
        type=ExecutionType.SCAN,
        metadata={"url": body.url}
    ))
    scan_id = execution.execution_id
    
    scan_log = ScanLogCollector()
    
    artifact_service = ArtifactService()
    started_at = datetime.now().isoformat()

    options = ScanOptions(
        url=body.url,
        headless=not body.headed,
    )

    scan_log.add(f"Scan started: {body.url}")
    scan_log.add(f"Scan ID: {scan_id}")
    scan_log.add(f"Browser mode: {options.browser_mode}")

    try:
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
        result = await asyncio.to_thread(service.scan_url, options, readiness_config=readiness_config)
        scan_log.add("Browser scan completed")

        completed_at = datetime.now().isoformat()
        duration_seconds = result["load_time"]

        scan_log.add("Saving screenshot...")
        screenshot_url = await artifact_service.save_screenshot(scan_id, result["screenshot_bytes"])

        analysis_dict = result["analysis"].model_dump(mode="json")
        readiness_dict = result.get("readiness")
        scan_log.add("Saving analysis artifacts...")
        await artifact_service.save_analysis_artifacts(scan_id, analysis_dict, readiness_dict)

        app_version = getattr(request.app, "version", "unknown")
        report = _build_report(
            scan_id=scan_id,
            url=body.url,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            browser_mode=options.browser_mode,
            status=ScanStatus.COMPLETED.value,
            result=result,
            app_version=app_version,
        )
        scan_log.add("Saving master report...")
        await artifact_service.save_report(scan_id, report)

        scan_log.add("Scan completed successfully")
        await artifact_service.save_scan_log(scan_id, scan_log.to_serializable())

        await execution_service.update_status(project_id, scan_id, ExecutionStatus.COMPLETED)

        logger.info(f"Scan artifacts saved for {scan_id}")

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
        logger.warning(f"Scan failed for {body.url}: {exc}")

        scan_log.add(f"Scan failed: {exc}")
        try:
            failed_report = {
                "scan_info": {
                    "scan_id": scan_id,
                    "url": body.url,
                    "started_at": started_at,
                    "completed_at": datetime.now().isoformat(),
                    "duration_seconds": 0,
                    "browser_mode": options.browser_mode,
                    "status": ScanStatus.FAILED.value,
                },
                "error": str(exc),
            }
            await artifact_service.save_report(scan_id, failed_report)
            await artifact_service.save_scan_log(scan_id, scan_log.to_serializable())
        except Exception as persist_exc:
            logger.error(f"Failed to persist failed scan artifacts: {persist_exc}")

        await execution_service.update_status(project_id, scan_id, ExecutionStatus.FAILED)

        return JSONResponse(
            status_code=502,
            content={
                "success": False,
                "scan_id": scan_id,
                "detail": str(exc),
            },
        )
