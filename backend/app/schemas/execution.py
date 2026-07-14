from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel
from app.models.execution_models import ExecutionType, ExecutionStatus

class ExecutionCreate(BaseModel):
    project_id: str
    type: ExecutionType
    metadata: dict[str, Any] = {}

class ExecutionResponse(BaseModel):
    execution_id: str
    project_id: str
    type: ExecutionType
    status: ExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    metadata: dict[str, Any]

class ExecutionListResponse(BaseModel):
    executions: list[ExecutionResponse]
    total: int
