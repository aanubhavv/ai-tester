from typing import Any, Optional
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form

from app.schemas.knowledge import DocumentResponse, DocumentListResponse
from app.models.knowledge_models import DocumentType
from app.services.knowledge_service import knowledge_service

router = APIRouter()

@router.post("/{project_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(""),
    document_type: DocumentType = Form(DocumentType.OTHER)
) -> Any:
    """
    Upload a new knowledge document for a project.
    """
    doc = knowledge_service.upload_document(
        project_id=project_id,
        file=file,
        title=title,
        description=description,
        document_type=document_type
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    return doc

@router.get("/{project_id}/documents", response_model=DocumentListResponse)
def list_documents(project_id: str) -> Any:
    """
    List all knowledge documents for a project.
    """
    docs = knowledge_service.list_documents(project_id)
    return {"documents": docs, "total": len(docs)}

@router.get("/{project_id}/documents/{document_id}", response_model=DocumentResponse)
def get_document(project_id: str, document_id: str) -> Any:
    """
    Get a document by ID.
    """
    doc = knowledge_service.get_document(project_id, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found in project {project_id}"
        )
    return doc

@router.delete("/{project_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(project_id: str, document_id: str) -> None:
    """
    Delete a document.
    """
    success = knowledge_service.delete_document(project_id, document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found or could not be deleted"
        )
    return None
