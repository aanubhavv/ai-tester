from typing import Any
from fastapi import APIRouter, HTTPException, status

from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
from app.schemas.execution import ExecutionListResponse
from app.services.project_service import project_service
from app.services.execution_service import execution_service

router = APIRouter()

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(data: ProjectCreate) -> Any:
    """
    Create a new project.
    """
    project = await project_service.create_project(data)
    return project

@router.get("/", response_model=ProjectListResponse)
async def list_projects() -> Any:
    """
    List all projects.
    """
    projects = await project_service.list_projects()
    return {"projects": projects, "total": len(projects)}

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str) -> Any:
    """
    Get a project by ID.
    """
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    project_dict = project.model_dump()
    project_dict["project_context"] = await project_service.get_project_context(project_id)
    return project_dict

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, data: ProjectUpdate) -> Any:
    """
    Update a project by ID.
    """
    project = await project_service.update_project(project_id, data)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
        
    project_dict = project.model_dump()
    project_dict["project_context"] = await project_service.get_project_context(project_id)
    return project_dict

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str) -> None:
    """
    Delete a project.
    """
    success = await project_service.delete_project(project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found or could not be deleted"
        )
    return None

@router.get("/{project_id}/executions", response_model=ExecutionListResponse)
async def list_project_executions(project_id: str) -> Any:
    """
    List all executions for a project.
    """
    # Verify project exists
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
        
    executions = await execution_service.list_executions(project_id)
    return {"executions": executions, "total": len(executions)}
