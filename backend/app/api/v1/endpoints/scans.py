"""
Scan History Endpoints
======================

Read-only endpoints for retrieving persisted scan artifacts.

These endpoints are the query side of the scan system:
    - POST /api/v1/scan  → creates a scan (in scan.py)
    - GET  /api/v1/scans → reads scans (this file)

All three endpoints delegate entirely to ArtifactService. They contain
zero business logic — just input validation, service delegation, and
response formatting.

Why a separate file from scan.py?
    scan.py handles scan creation (POST). This file handles scan retrieval
    (GET). Separating reads from writes keeps each file focused and avoids
    a bloated scan.py.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings
from app.schemas.report import ScanListItemSchema
from app.services.artifact_service import ArtifactService

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_artifact_service() -> ArtifactService:
    """
    Create an ArtifactService instance with the configured directory.

    This is a factory function rather than a FastAPI Depends() because
    ArtifactService is stateless — creating a new instance per request
    is cheap (no connections to manage). If ArtifactService later gains
    a cache or connection pool, this becomes a proper dependency.
    """
    return ArtifactService(artifacts_dir=settings.artifacts_dir)


@router.get("/scans", response_model=list[ScanListItemSchema])
def list_scans():
    """
    List all available scans with summary information.

    Returns scan summaries sorted by creation time (most recent first).
    Each item contains just enough for a scan history list UI.

    Returns:
        List of ScanListItemSchema objects.
    """
    service = _get_artifact_service()
    scan_list = service.list_scans()
    return [ScanListItemSchema(**scan) for scan in scan_list]


@router.get("/scans/{scan_id}")
def get_scan_report(scan_id: str):
    """
    Retrieve the full master report for a specific scan.

    Returns the complete report.json contents, which includes:
    scan metadata, full analysis, readiness report, and version info.

    Args:
        scan_id: The unique scan identifier (e.g., "scan_20260713_143055_a81c").

    Returns:
        The master report as JSON.

    Raises:
        HTTPException 404: If the scan doesn't exist or has no report.
    """
    service = _get_artifact_service()

    if not service.scan_exists(scan_id):
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found.")

    report = service.get_scan_report(scan_id)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"Report for scan '{scan_id}' not found. The scan may have failed.",
        )

    return report


@router.get("/scans/{scan_id}/screenshot")
def get_scan_screenshot(scan_id: str):
    """
    Serve the screenshot PNG for a specific scan.

    Returns the image file directly with the correct content type,
    ready for display in a browser or download by an API client.

    Args:
        scan_id: The unique scan identifier.

    Returns:
        FileResponse with media_type="image/png".

    Raises:
        HTTPException 404: If the scan or screenshot doesn't exist.
    """
    service = _get_artifact_service()

    if not service.scan_exists(scan_id):
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found.")

    screenshot_path = service.get_screenshot_path(scan_id)
    if screenshot_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"Screenshot for scan '{scan_id}' not found.",
        )

    return FileResponse(
        path=str(screenshot_path),
        media_type="image/png",
        filename=f"{scan_id}_screenshot.png",
    )
