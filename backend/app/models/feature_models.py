"""
Feature & Flow Domain Models
============================

Domain types for Features and User Flows.
Features break down the application into logical testable components.
User Flows define business-critical pathways through those features.
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field

def generate_feature_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    short_hex = uuid.uuid4().hex[:4]
    return f"feat_{short_hex}_{timestamp}"

def generate_flow_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    short_hex = uuid.uuid4().hex[:4]
    return f"flow_{short_hex}_{timestamp}"

class FeatureModel(BaseModel):
    feature_id: str = Field(default_factory=generate_feature_id)
    project_id: str
    name: str
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class FlowStep(BaseModel):
    step_number: int
    action: str
    description: str = ""

class UserFlowModel(BaseModel):
    flow_id: str = Field(default_factory=generate_flow_id)
    project_id: str
    feature_id: str | None = None
    name: str
    description: str = ""
    steps: list[FlowStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
