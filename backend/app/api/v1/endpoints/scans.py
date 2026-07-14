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


from pathlib import Path
from app.services.project_service import PROJECTS_ROOT

@router.get("/scans", response_model=list[ScanListItemSchema])
def list_scans():
    """
    List all available scans with summary information.

    Returns scan summaries sorted by creation time (most recent first).
    Each item contains just enough for a scan history list UI.

    Returns:
        List of ScanListItemSchema objects.
    """
    # Get legacy scans
    legacy_service = ArtifactService(artifacts_dir=settings.artifacts_dir)
    scan_list = legacy_service.list_scans()
    
    # Get project executions
    if PROJECTS_ROOT.exists():
        for project_dir in PROJECTS_ROOT.iterdir():
            if project_dir.is_dir():
                executions_dir = project_dir / "executions"
                if executions_dir.exists():
                    for exec_dir in executions_dir.iterdir():
                        if exec_dir.is_dir():
                            proj_service = ArtifactService(artifacts_dir=str(exec_dir / "artifacts"))
                            # list_scans returns list of dicts, but will only find the 1 scan for this execution
                            scan_list.extend(proj_service.list_scans())
                            
    # Sort unified list by creation time
    scan_list.sort(key=lambda x: x.get("created_at") or "", reverse=True)
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
    service = ArtifactService.get_for_scan(scan_id)

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
    service = ArtifactService.get_for_scan(scan_id)

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
