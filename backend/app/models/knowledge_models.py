"""
Knowledge Domain Models
=======================

Domain types for managing project knowledge.
Knowledge includes uploaded documents like PRDs, architectural notes,
and reference materials that define how the product should behave.
"""

import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class DocumentType(str, Enum):
    PRD = "prd"
    NOTES = "notes"
    FEATURE_DESCRIPTION = "feature_description"
    BUSINESS_CONTEXT = "business_context"
    ACCEPTANCE_CRITERIA = "acceptance_criteria"
    OTHER = "other"

def generate_document_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    short_hex = uuid.uuid4().hex[:4]
    return f"doc_{short_hex}_{timestamp}"

class DocumentModel(BaseModel):
    document_id: str = Field(default_factory=generate_document_id)
    project_id: str
    title: str
    description: str = ""
    document_type: DocumentType = DocumentType.OTHER
    filename: str
    file_url: str | None = None
    file_data: bytes | None = None
    content: str | None = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
