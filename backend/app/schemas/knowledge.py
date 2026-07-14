from datetime import datetime
from pydantic import BaseModel
from app.models.knowledge_models import DocumentType

class DocumentResponse(BaseModel):
    document_id: str
    project_id: str
    title: str
    description: str
    document_type: DocumentType
    filename: str
    uploaded_at: datetime

class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
