from typing import Any
from fastapi import APIRouter, HTTPException, status

from app.schemas.feature import (
    FeatureCreate, FeatureResponse, FeatureListResponse,
    UserFlowCreate, UserFlowResponse, UserFlowListResponse
)
from app.services.feature_service import feature_service

router = APIRouter()

# --- Features ---

@router.post("/{project_id}/features", response_model=FeatureResponse, status_code=status.HTTP_201_CREATED)
def create_feature(project_id: str, data: FeatureCreate) -> Any:
    feature = feature_service.create_feature(project_id, data)
    if not feature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")
    return feature

@router.get("/{project_id}/features", response_model=FeatureListResponse)
def list_features(project_id: str) -> Any:
    features = feature_service.list_features(project_id)
    return {"features": features, "total": len(features)}

@router.get("/{project_id}/features/{feature_id}", response_model=FeatureResponse)
def get_feature(project_id: str, feature_id: str) -> Any:
    feature = feature_service.get_feature(project_id, feature_id)
    if not feature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature not found")
    return feature

@router.delete("/{project_id}/features/{feature_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feature(project_id: str, feature_id: str) -> None:
    success = feature_service.delete_feature(project_id, feature_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature not found")
    return None

# --- User Flows ---

@router.post("/{project_id}/flows", response_model=UserFlowResponse, status_code=status.HTTP_201_CREATED)
def create_flow(project_id: str, data: UserFlowCreate) -> Any:
    flow = feature_service.create_flow(project_id, data)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")
    return flow

@router.get("/{project_id}/flows", response_model=UserFlowListResponse)
def list_flows(project_id: str) -> Any:
    flows = feature_service.list_flows(project_id)
    return {"flows": flows, "total": len(flows)}

@router.get("/{project_id}/flows/{flow_id}", response_model=UserFlowResponse)
def get_flow(project_id: str, flow_id: str) -> Any:
    flow = feature_service.get_flow(project_id, flow_id)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")
    return flow

@router.delete("/{project_id}/flows/{flow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_flow(project_id: str, flow_id: str) -> None:
    success = feature_service.delete_flow(project_id, flow_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")
    return None
