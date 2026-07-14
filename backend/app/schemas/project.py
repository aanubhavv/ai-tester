from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    primary_url: Optional[str] = ""

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    primary_url: Optional[str] = None
    project_context: Optional[str] = None

class ProjectResponse(BaseModel):
    project_id: str
    name: str
    description: str
    primary_url: str
    project_context: str = ""
    created_at: datetime
    updated_at: datetime

class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int
