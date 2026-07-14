import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse

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
def compare_scans(
    request: ComparisonRequest
):
    """
    Perform a visual regression comparison between two scan artifacts.
    """
    
    # Create execution record
    exec_data = ExecutionCreate(
        project_id=request.project_id,
        type=ExecutionType.VISUAL_COMPARISON,
        metadata={"baseline_scan_id": request.baseline_scan_id, "current_scan_id": request.current_scan_id}
    )
    execution = execution_service.create_execution(exec_data)
    
    # Ensure comparison is saved in the execution's artifact dir
    artifact_service = ArtifactService(artifacts_dir=str(execution_service._get_execution_dir(request.project_id, execution.execution_id) / "artifacts"))
    comparison_service = ComparisonService(artifact_service=artifact_service)
    
    try:
        execution_service.update_status(request.project_id, execution.execution_id, ExecutionStatus.RUNNING)
        report_dict = comparison_service.compare_scans(request)
        
        comparison_id = report_dict["info"]["comparison_id"]
        # In the new architecture, the image diff URL should just be the comparison_id?
        # Let's keep the global endpoint working by ensuring the image is saved where get_diff_image looks, 
        # but actually wait: the frontend uses /api/v1/comparisons/{comparison_id}/diff.
        # But we changed artifact_service to save in the execution dir!
        # If we do that, we need to update get_diff_image.
        
        diff_image_url = f"{settings.api_prefix}/projects/{request.project_id}/executions/{execution.execution_id}/diff"
        
        # We need to save the comparison_id to the execution metadata
        execution = execution_service.get_execution(request.project_id, execution.execution_id)
        execution.metadata["comparison_id"] = comparison_id
        execution.metadata["passed"] = report_dict["status"] == "passed"
        execution.metadata["statistics"] = report_dict["statistics"]
        execution_service.save_execution(execution)
        
        execution_service.update_status(request.project_id, execution.execution_id, ExecutionStatus.COMPLETED)
        
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
        execution_service.update_status(request.project_id, execution.execution_id, ExecutionStatus.FAILED)
        logger.error(f"Comparison failed: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        execution_service.update_status(request.project_id, execution.execution_id, ExecutionStatus.FAILED)
        logger.exception("Unexpected error during comparison")
        raise HTTPException(status_code=500, detail="Internal server error during comparison.")

@router.get("/comparisons/{comparison_id}/diff")
def get_diff_image(comparison_id: str):
    """
    Serve the generated diff image for a comparison (legacy global artifacts).
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

@router.get("/projects/{project_id}/executions/{execution_id}/diff")
def get_execution_diff_image(project_id: str, execution_id: str):
    """
    Serve the generated diff image for a comparison in a specific execution.
    """
    exec_dir = execution_service._get_execution_dir(project_id, execution_id)
    if not exec_dir.exists():
        raise HTTPException(status_code=404, detail="Execution directory not found")
        
    # Read the execution metadata to find comparison_id
    execution = execution_service.get_execution(project_id, execution_id)
    if not execution or "comparison_id" not in execution.metadata:
        raise HTTPException(status_code=404, detail="Comparison ID not found in execution metadata")
        
    comparison_id = execution.metadata["comparison_id"]
    
    # We set artifacts_dir = exec_dir / "artifacts" when we created it.
    artifact_service = ArtifactService(artifacts_dir=str(exec_dir / "artifacts"))
    comp_dir = artifact_service._comparison_dir(comparison_id)
    diff_path = comp_dir / "diff.png"
    
    if not diff_path.exists():
        raise HTTPException(status_code=404, detail="Diff image not found")
        
    return FileResponse(
        path=diff_path,
        media_type="image/png",
        filename=f"{comparison_id}_diff.png"
    )
