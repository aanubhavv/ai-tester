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

router = APIRouter()

class GenerationRequest(BaseModel):
    feature_name: str
    suite_name: str

@router.post("/{project_id}/test-cases/generate", status_code=status.HTTP_202_ACCEPTED)
def generate_test_cases(project_id: str, request: GenerationRequest, background_tasks: BackgroundTasks) -> Any:
    """
    Triggers AI Test Case Generation for a specific suite.
    """
    suites_data = planning_service.get_artifact(project_id, "test_suites.json")
    if not suites_data:
        raise HTTPException(status_code=404, detail="Test Suites not found. Run planning first.")
        
    suites = SuiteGenerationResult(**suites_data)
    
    # Find the target suite
    target_suite = next((s for s in suites.suites if s.suite_name == request.suite_name), None)
    if not target_suite:
        raise HTTPException(status_code=404, detail=f"Suite {request.suite_name} not found.")

    def background_generation():
        # Get context (requirements and risks)
        reqs = planning_service.get_artifact(project_id, "requirements.json")
        risks = planning_service.get_artifact(project_id, "risks.json")
        
        req_str = str(reqs) if reqs else "None"
        risk_str = str(risks) if risks else "None"
        
        # Add Knowledge Base documents to context
        from app.services.knowledge_service import knowledge_service
        docs = knowledge_service.list_documents(project_id)
        docs_content = []
        for doc in docs:
            content = knowledge_service.get_document_content(project_id, doc.document_id)
            if content and not content.startswith("[Binary"):
                docs_content.append(f"--- Document: {doc.title} ---\n{content}\n")
        
        if docs_content:
            req_str += "\n\n=== ADDITIONAL KNOWLEDGE BASE CONTEXT ===\n" + "\n".join(docs_content)
        
        try:
            generated_tests = generation_service.generate_for_suite(
                project_id=project_id,
                suite_name=target_suite.suite_name,
                feature_name=target_suite.feature_name,
                high_level_scenarios=target_suite.high_level_test_cases,
                related_requirements=req_str,
                risk_context=risk_str
            )
            generation_service.save_test_cases(project_id, generated_tests)
        except Exception as e:
            print(f"Failed to generate tests for suite {request.suite_name}: {e}")

    background_tasks.add_task(background_generation)
    return {"message": f"Generation started for suite {request.suite_name}."}

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
        
    updated_test = version_service.bump_version(target, updates)
    
    # Save back
    new_list = [updated_test if t.id == test_id else t for t in tests]
    
    # The generation service save method merges by ID, so we just overwrite the whole list directly 
    # to avoid merging logic bypassing updates.
    tests_dir = generation_service._get_project_dir(project_id) / "test_cases"
    file_path = tests_dir / "test_cases.json"
    import json
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump([tc.model_dump() for tc in new_list], f, indent=2)
        
    return updated_test

@router.post("/{project_id}/test-cases/{test_id}/approve", response_model=TestCase)
def approve_test_case(project_id: str, test_id: str) -> Any:
    return update_test_case(project_id, test_id, {"status": TestCaseStatus.APPROVED})

@router.get("/{project_id}/test-cases/export/csv")
def export_csv(project_id: str) -> Any:
    from fastapi.responses import PlainTextResponse
    tests = generation_service.get_test_cases(project_id)
    csv_data = export_service.export_to_csv(tests)
    return PlainTextResponse(content=csv_data, media_type="text/csv")
