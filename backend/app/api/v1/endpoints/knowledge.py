from typing import Any, Optional
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Response
from fastapi.responses import RedirectResponse

from app.schemas.knowledge import DocumentResponse, DocumentListResponse
from app.models.knowledge_models import DocumentType
from app.services.knowledge_service import knowledge_service

router = APIRouter()

@router.post("/{project_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(""),
    document_type: DocumentType = Form(DocumentType.OTHER)
) -> Any:
    """
    Upload a new knowledge document for a project.
    """
    doc = await knowledge_service.upload_document(
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
async def list_documents(project_id: str) -> Any:
    """
    List all knowledge documents for a project.
    """
    docs = await knowledge_service.list_documents(project_id)
    return {"documents": docs, "total": len(docs)}

@router.get("/{project_id}/documents/{document_id}", response_model=DocumentResponse)
async def get_document(project_id: str, document_id: str) -> Any:
    """
    Get a document by ID.
    """
    doc = await knowledge_service.get_document(project_id, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found in project {project_id}"
        )
    return doc

@router.get("/{project_id}/documents/{document_id}/content")
async def get_document_content(project_id: str, document_id: str) -> Any:
    """
    Get the raw text content of a document.
    """
    content = await knowledge_service.get_document_content(project_id, document_id)
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document content not found for {document_id}"
        )
    return {"content": content}

@router.get("/{project_id}/documents/{document_id}/file")
async def get_document_file(project_id: str, document_id: str) -> Any:
    """
    Get the raw document file for viewing inline.
    """
    doc = await knowledge_service.get_document(project_id, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found for {document_id}"
        )
        
    if doc.file_data:
        media_type = "application/pdf" if doc.filename.lower().endswith(".pdf") else "application/octet-stream"
        return Response(content=doc.file_data, media_type=media_type)
        
    if doc.file_url:
        return RedirectResponse(url=doc.file_url)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Document file not found for {document_id}"
    )

@router.delete("/{project_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(project_id: str, document_id: str) -> None:
    """
    Delete a document.
    """
    success = await knowledge_service.delete_document(project_id, document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found or could not be deleted"
        )
    return None
