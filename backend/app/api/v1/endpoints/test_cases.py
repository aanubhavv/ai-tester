from typing import Any, List, Dict
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel

from app.services.test_generation.generation_service import generation_service
from app.services.test_generation.coverage_analyzer import coverage_analyzer
from app.services.test_generation.duplicate_detector import duplicate_detector
from app.services.test_generation.version_service import version_service
from app.services.test_generation.export_service import export_service
from app.services.planning.planning_service import planning_service

from app.schemas.test_cases.models import TestCase, TestCaseStatus, CoverageReport
from app.schemas.planning.requirements import StructuredRequirements
from app.schemas.planning.features import FeatureExtractionResult
from app.schemas.planning.strategy import SuiteGenerationResult
from app.schemas.execution import BulkActionRequest
from app.services.execution.queue import execution_queue
from app.services.script_generation.generator import script_generator
from app.services.playwright_execution.runner import execution_runner, PlaywrightExecutionService
from datetime import datetime

router = APIRouter()

@router.post("/{project_id}/test-cases/generate", status_code=status.HTTP_202_ACCEPTED)
def generate_test_cases(project_id: str, background_tasks: BackgroundTasks) -> Any:
    """
    Triggers AI Test Case Generation directly from Knowledge Base and Context.
    """
    def background_generation():
        from app.services.project_service import project_service
        project = project_service.get_project(project_id)
        
        project_context = project_service.get_project_context(project_id)
        if not project_context:
            project_context = "None provided."        
        # Add Knowledge Base documents to context
        from app.services.knowledge_service import knowledge_service
        docs = knowledge_service.list_documents(project_id)
        docs_content = []
        for doc in docs:
            content = knowledge_service.get_document_content(project_id, doc.document_id)
            if content and not content.startswith("[Binary"):
                docs_content.append(f"--- Document: {doc.title} ---\n{content}\n")
        
        docs_context_str = "\n".join(docs_content) if docs_content else "No knowledge base documents."
        
        try:
            generated_tests = generation_service.generate_direct(
                project_id=project_id,
                project_context=project_context,
                docs_content=docs_context_str
            )
            generation_service.save_test_cases(project_id, generated_tests)
        except Exception as e:
            print(f"Failed to generate tests: {e}")

    background_tasks.add_task(background_generation)
    return {"message": "Direct Generation started."}

@router.get("/{project_id}/test-cases", response_model=List[TestCase])
def get_test_cases(project_id: str) -> Any:
    return generation_service.get_test_cases(project_id)

@router.get("/{project_id}/test-cases/coverage", response_model=CoverageReport)
def get_coverage(project_id: str) -> Any:
    tests = generation_service.get_test_cases(project_id)
    
    reqs_data = planning_service.get_artifact(project_id, "requirements.json")
    features_data = planning_service.get_artifact(project_id, "features.json")
    
    if not reqs_data or not features_data:
        raise HTTPException(status_code=400, detail="Cannot calculate coverage without requirements and features.")
        
    reqs = StructuredRequirements(**reqs_data)
    features = FeatureExtractionResult(**features_data)
    
    return coverage_analyzer.analyze(tests, reqs, features)

@router.get("/{project_id}/test-cases/duplicates")
def get_duplicates(project_id: str) -> Any:
    tests = generation_service.get_test_cases(project_id)
    dupes = duplicate_detector.detect_duplicates(tests)
    return {"duplicates": dupes}

@router.patch("/{project_id}/test-cases/{test_id}", response_model=TestCase)
def update_test_case(project_id: str, test_id: str, updates: dict) -> Any:
    tests = generation_service.get_test_cases(project_id)
    target = next((t for t in tests if t.id == test_id), None)
    
    if not target:
        raise HTTPException(status_code=404, detail="Test Case not found.")
        
    target_dict = target.model_dump()
    target_dict.update(updates)
    updated_test = TestCase(**target_dict)
    
    # Save back to JSON and XLSX
    new_list = [updated_test if t.id == test_id else t for t in tests]
    generation_service.save_test_cases(project_id, new_list)
        
    return updated_test

@router.post("/{project_id}/test-cases/{test_id}/approve", response_model=TestCase)
def approve_test_case(project_id: str, test_id: str) -> Any:
    return update_test_case(project_id, test_id, {"status": TestCaseStatus.APPROVED})

@router.get("/{project_id}/test-cases/export/xlsx")
def export_xlsx(project_id: str) -> Any:
    from fastapi.responses import FileResponse
    import os
    
    tests_dir = generation_service._get_project_dir(project_id) / "test_cases"
    xlsx_path = tests_dir / "test_cases.xlsx"
    
    if not xlsx_path.exists():
        raise HTTPException(status_code=404, detail="No exported test cases found.")
        
    return FileResponse(path=xlsx_path, filename=f"test_cases_{project_id}.xlsx")

def _update_tc_internal(project_id: str, tc_id: str, updates: dict):
    tests = generation_service.get_test_cases(project_id)
    target = next((t for t in tests if t.id == tc_id), None)
    if not target:
        return
    
    target_dict = target.model_dump()
    target_dict.update(updates)
    updated_test = TestCase(**target_dict)
    
    new_list = [updated_test if t.id == tc_id else t for t in tests]
    generation_service.save_test_cases(project_id, new_list)

async def _generation_job(project_id: str, tc_id: str):
    # Set status to Generating
    _update_tc_internal(project_id, tc_id, {"script_status": "Generating"})
    
    # Get test case
    tests = generation_service.get_test_cases(project_id)
    tc = next((t for t in tests if t.id == tc_id), None)
    if not tc: return
    
    # Generate
    script_content = await script_generator.generate_script(project_id, tc)
    
    if script_content:
        _update_tc_internal(project_id, tc_id, {
            "script_status": "Generated",
            "script": script_content,
            "script_metadata": {
                "generated_at": datetime.utcnow().isoformat()
            }
        })
    else:
        _update_tc_internal(project_id, tc_id, {"script_status": "Failed"})

async def _execution_job(project_id: str, tc_id: str):
    _update_tc_internal(project_id, tc_id, {"execution_status": "Running"})
    
    tests = generation_service.get_test_cases(project_id)
    tc = next((t for t in tests if t.id == tc_id), None)
    if not tc: return
    
    result = await execution_runner.execute_script(project_id, tc)
    
    _update_tc_internal(project_id, tc_id, {
        "execution_status": result["status"],
        "last_execution_time": result["duration"],
        "last_execution_error": result["error"],
        "execution_logs": result["logs"],
        "last_execution_timestamp": datetime.utcnow().isoformat()
    })

@router.post("/{project_id}/test-cases/scripts/generate")
async def bulk_generate_scripts(project_id: str, req: BulkActionRequest) -> Any:
    for tc_id in req.test_case_ids:
        _update_tc_internal(project_id, tc_id, {"script_status": "Queued"})
        execution_queue.enqueue(
            job_id=f"gen_{tc_id}",
            job_type="generate",
            coro=_generation_job(project_id, tc_id)
        )
    return {"message": f"Queued {len(req.test_case_ids)} script generation jobs"}

@router.post("/{project_id}/test-cases/scripts/execute")
async def bulk_execute_scripts(project_id: str, req: BulkActionRequest) -> Any:
    for tc_id in req.test_case_ids:
        _update_tc_internal(project_id, tc_id, {"execution_status": "Queued"})
        execution_queue.enqueue(
            job_id=f"exe_{tc_id}",
            job_type="execute",
            coro=_execution_job(project_id, tc_id)
        )
    return {"message": f"Queued {len(req.test_case_ids)} script execution jobs"}

@router.post("/{project_id}/test-cases/scripts/stop")
async def bulk_stop_execution(project_id: str, req: BulkActionRequest) -> Any:
    for tc_id in req.test_case_ids:
        # We can cancel via PlaywrightExecutionService
        PlaywrightExecutionService.cancel_execution(project_id, tc_id)
        # Update the status to Stopped
        _update_tc_internal(project_id, tc_id, {"execution_status": "Stopped", "last_execution_error": "Execution stopped by user."})
    return {"message": f"Stopped {len(req.test_case_ids)} script execution jobs"}
