from typing import Optional
from datetime import datetime
from pydantic import BaseModel

# Features
class FeatureCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class FeatureResponse(BaseModel):
    feature_id: str
    project_id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime

class FeatureListResponse(BaseModel):
    features: list[FeatureResponse]
    total: int

# Flows
class FlowStepSchema(BaseModel):
    step_number: int
    action: str
    description: Optional[str] = ""

class UserFlowCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    feature_id: Optional[str] = None
    steps: list[FlowStepSchema] = []

class UserFlowResponse(BaseModel):
    flow_id: str
    project_id: str
    feature_id: Optional[str] = None
    name: str
    description: str
    steps: list[FlowStepSchema]
    created_at: datetime
    updated_at: datetime

class UserFlowListResponse(BaseModel):
    flows: list[UserFlowResponse]
    total: int
