import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse

from app.schemas.comparison import ComparisonRequest, ComparisonResponse
from app.services.comparison_service import ComparisonService, ComparisonError
from app.services.artifact_service import ArtifactService
from app.core.config import settings

from app.models.execution_models import ExecutionType, ExecutionStatus
from app.schemas.execution import ExecutionCreate
from app.services.execution_service import execution_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/compare", response_model=ComparisonResponse)
async def compare_scans(
    request: ComparisonRequest
):
    """
    Perform a visual regression comparison between two scan artifacts.
    """
    
    exec_data = ExecutionCreate(
        project_id=request.project_id,
        type=ExecutionType.VISUAL_COMPARISON,
        metadata={"baseline_scan_id": request.baseline_scan_id, "current_scan_id": request.current_scan_id}
    )
    execution = await execution_service.create_execution(exec_data)
    
    artifact_service = ArtifactService()
    comparison_service = ComparisonService(artifact_service=artifact_service)
    
    try:
        await execution_service.update_status(request.project_id, execution.execution_id, ExecutionStatus.RUNNING)
        report_dict = await comparison_service.compare_scans(request)
        
        comparison_id = report_dict["info"]["comparison_id"]
        diff_image_url = f"{settings.api_prefix}/projects/{request.project_id}/executions/{execution.execution_id}/diff"
        
        execution = await execution_service.get_execution(request.project_id, execution.execution_id)
        execution.metadata["comparison_id"] = comparison_id
        execution.metadata["passed"] = report_dict["status"] == "passed"
        execution.metadata["statistics"] = report_dict["statistics"]
        await execution_service.save_execution(execution)
        
        await execution_service.update_status(request.project_id, execution.execution_id, ExecutionStatus.COMPLETED)
        
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
        await execution_service.update_status(request.project_id, execution.execution_id, ExecutionStatus.FAILED)
        logger.error(f"Comparison failed: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        await execution_service.update_status(request.project_id, execution.execution_id, ExecutionStatus.FAILED)
        logger.exception("Unexpected error during comparison")
        raise HTTPException(status_code=500, detail="Internal server error during comparison.")

@router.get("/comparisons/{comparison_id}/diff")
async def get_diff_image(comparison_id: str):
    """
    Redirect to the Cloudinary URL for the comparison diff image.
    """
    artifact_service = ArtifactService()
    diff_url = await artifact_service.get_diff_image_path(comparison_id)
    
    if not diff_url:
        raise HTTPException(status_code=404, detail="Diff image not found")
        
    return RedirectResponse(url=diff_url)

@router.get("/projects/{project_id}/executions/{execution_id}/diff")
async def get_execution_diff_image(project_id: str, execution_id: str):
    """
    Redirect to the Cloudinary URL for the diff image generated in this execution.
    """
    execution = await execution_service.get_execution(project_id, execution_id)
    if not execution or "comparison_id" not in execution.metadata:
        raise HTTPException(status_code=404, detail="Comparison ID not found in execution metadata")
        
    comparison_id = execution.metadata["comparison_id"]
    
    artifact_service = ArtifactService()
    diff_url = await artifact_service.get_diff_image_path(comparison_id)
    
    if not diff_url:
        raise HTTPException(status_code=404, detail="Diff image not found")
        
    return RedirectResponse(url=diff_url)
