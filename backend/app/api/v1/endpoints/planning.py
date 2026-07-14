from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status, BackgroundTasks

from app.services.planning.planning_service import planning_service

router = APIRouter()

@router.post("/{project_id}/planning/generate", status_code=status.HTTP_202_ACCEPTED)
def generate_planning(project_id: str, background_tasks: BackgroundTasks) -> Any:
    """
    Triggers the AI Planning pipeline for a project.
    Runs in the background since it involves multiple LLM calls.
    """
    # Verify project exists
    from app.services.project_service import project_service
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    background_tasks.add_task(planning_service.generate_planning, project_id)
    return {"message": "Planning generation started in the background."}

@router.get("/{project_id}/planning/requirements")
def get_requirements(project_id: str) -> Any:
    data = planning_service.get_artifact(project_id, "requirements.json")
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirements not found")
    return data

@router.get("/{project_id}/planning/features")
def get_features(project_id: str) -> Any:
    data = planning_service.get_artifact(project_id, "features.json")
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Features not found")
    return data

@router.get("/{project_id}/planning/flows")
def get_flows(project_id: str) -> Any:
    data = planning_service.get_artifact(project_id, "user_flows.json")
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flows not found")
    return data

@router.get("/{project_id}/planning/risks")
def get_risks(project_id: str) -> Any:
    data = planning_service.get_artifact(project_id, "risks.json")
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risks not found")
    return data

@router.get("/{project_id}/planning/strategy")
def get_strategy(project_id: str) -> Any:
    data = planning_service.get_artifact(project_id, "testing_strategy.json")
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    return data

@router.get("/{project_id}/planning/suites")
def get_suites(project_id: str) -> Any:
    data = planning_service.get_artifact(project_id, "test_suites.json")
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test Suites not found")
    return data
