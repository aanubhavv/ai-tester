"""
Project Domain Models
=====================

Core identity and domain types for Projects.
A Project serves as the root container for all QA activities, 
including knowledge, features, flows, and executions.
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field

def generate_project_id() -> str:
    """
    Generate a unique project identifier.
    Format: proj_<4-char-hex>_<timestamp>
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    short_hex = uuid.uuid4().hex[:4]
    return f"proj_{short_hex}_{timestamp}"

class ProjectModel(BaseModel):
    """
    Internal domain model representing a Project.
    """
    project_id: str = Field(default_factory=generate_project_id)
    name: str
    description: str = ""
    primary_url: str = ""
    max_crawl_pages: int = 5
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
