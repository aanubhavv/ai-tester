import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse

from app.schemas.comparison import ComparisonRequest, ComparisonResponse
from app.services.comparison_service import ComparisonService, ComparisonError
from app.services.artifact_service import ArtifactService
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/compare", response_model=ComparisonResponse)
def compare_scans(
    request: ComparisonRequest
):
    """
    Perform a visual regression comparison between two scan artifacts.
    """
    
    artifact_service = ArtifactService(artifacts_dir=settings.artifacts_dir)
    comparison_service = ComparisonService(artifact_service=artifact_service)
    
    try:
        report_dict = comparison_service.compare_scans(request)
        
        comparison_id = report_dict["info"]["comparison_id"]
        diff_image_url = f"{settings.api_prefix}/comparisons/{comparison_id}/diff"
        
        return ComparisonResponse(
            comparison_id=comparison_id,
            baseline_scan_id=report_dict["info"]["baseline_scan_id"],
            current_scan_id=report_dict["info"]["current_scan_id"],
            passed=report_dict["status"] == "passed",
            statistics=report_dict["statistics"],
            changed_regions=report_dict["changed_regions"],
            warnings=report_dict.get("warnings", []),
            diff_image_url=diff_image_url,
        )
    except ComparisonError as exc:
        logger.error(f"Comparison failed: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during comparison")
        raise HTTPException(status_code=500, detail="Internal server error during comparison.")

@router.get("/comparisons/{comparison_id}/diff")
def get_diff_image(comparison_id: str):
    """
    Serve the generated diff image for a comparison.
    """
    artifact_service = ArtifactService(artifacts_dir=settings.artifacts_dir)
    comp_dir = artifact_service._comparison_dir(comparison_id)
    diff_path = comp_dir / "diff.png"
    
    if not diff_path.exists():
        raise HTTPException(status_code=404, detail="Diff image not found")
        
    return FileResponse(
        path=diff_path,
        media_type="image/png",
        filename=f"{comparison_id}_diff.png"
    )
