import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from app.schemas.report import ScanListItemSchema
from app.services.artifact_service import ArtifactService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/scans", response_model=list[ScanListItemSchema])
async def list_scans():
    """
    List all available scans with summary information.
    """
    service = ArtifactService()
    scan_list = await service.list_scans()
    
    # Sort unified list by creation time
    scan_list.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return [ScanListItemSchema(**scan) for scan in scan_list]


@router.get("/scans/{scan_id}")
async def get_scan_report(scan_id: str):
    """
    Retrieve the full master report for a specific scan.
    """
    service = ArtifactService()

    if not await service.scan_exists(scan_id):
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found.")

    report = await service.get_scan_report(scan_id)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"Report for scan '{scan_id}' not found. The scan may have failed.",
        )

    return report


@router.get("/scans/{scan_id}/screenshot")
async def get_scan_screenshot(scan_id: str):
    """
    Redirect to the screenshot URL in Cloudinary for a specific scan.
    """
    service = ArtifactService()

    if not await service.scan_exists(scan_id):
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found.")

    screenshot_url = await service.get_screenshot_path(scan_id)
    if not screenshot_url:
        raise HTTPException(
            status_code=404,
            detail=f"Screenshot for scan '{scan_id}' not found.",
        )

    return RedirectResponse(url=screenshot_url)
