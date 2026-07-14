"""
Execution Domain Models
=======================

Core identity and lifecycle types for Executions.
An Execution is a parent object for any automated or manual activity
(e.g., Website Scan, Visual Comparison, AI Analysis) that takes place
within a Project.
"""

import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class ExecutionType(str, Enum):
    SCAN = "scan"
    VISUAL_COMPARISON = "visual_comparison"
    AI_ANALYSIS = "ai_analysis"

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

def generate_execution_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_hex = uuid.uuid4().hex[:4]
    return f"exec_{timestamp}_{short_hex}"

class ExecutionModel(BaseModel):
    execution_id: str = Field(default_factory=generate_execution_id)
    project_id: str
    type: ExecutionType
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)
