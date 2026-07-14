import json
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import UploadFile
from app.models.knowledge_models import DocumentModel, DocumentType
from app.services.project_service import PROJECTS_ROOT, project_service

class KnowledgeService:
    """
    Service for managing Project Knowledge Documents.
    Documents metadata are stored in `projects/<project_id>/knowledge/` as JSON.
    The actual files are stored in `projects/<project_id>/uploads/`.
    """

    def _get_knowledge_dir(self, project_id: str) -> Path:
        return PROJECTS_ROOT / project_id / "knowledge"

    def _get_uploads_dir(self, project_id: str) -> Path:
        return PROJECTS_ROOT / project_id / "uploads"

    def upload_document(
        self, 
        project_id: str, 
        file: UploadFile, 
        title: str, 
        description: str = "",
        document_type: DocumentType = DocumentType.OTHER
    ) -> Optional[DocumentModel]:
        """Save an uploaded file and generate its metadata document."""
        project = project_service.get_project(project_id)
        if not project:
            return None

        # Prepare directories
        uploads_dir = self._get_uploads_dir(project_id)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        knowledge_dir = self._get_knowledge_dir(project_id)
        knowledge_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique ID for the document metadata
        from app.models.knowledge_models import generate_document_id
        doc_id = generate_document_id()

        # Save the physical file
        filename = file.filename or f"upload_{doc_id}"
        file_path = uploads_dir / f"{doc_id}_{filename}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Create metadata model
        doc = DocumentModel(
            document_id=doc_id,
            project_id=project_id,
            title=title or filename,
            description=description,
            document_type=document_type,
            filename=filename,
            file_path=str(file_path)
        )

        # Save metadata JSON
        doc_json_path = knowledge_dir / f"{doc_id}.json"
        with open(doc_json_path, "w") as f:
            f.write(doc.model_dump_json(indent=2))

        return doc

    def list_documents(self, project_id: str) -> List[DocumentModel]:
        """List all knowledge documents for a project."""
        docs = []
        knowledge_dir = self._get_knowledge_dir(project_id)
        if not knowledge_dir.exists():
            return docs

        for entry in knowledge_dir.iterdir():
            if entry.is_file() and entry.suffix == ".json":
                try:
                    with open(entry, "r") as f:
                        data = json.load(f)
                        docs.append(DocumentModel(**data))
                except Exception as e:
                    print(f"Error loading document from {entry}: {e}")

        docs.sort(key=lambda d: d.uploaded_at, reverse=True)
        return docs

    def get_document(self, project_id: str, document_id: str) -> Optional[DocumentModel]:
        """Get metadata for a specific document."""
        doc_path = self._get_knowledge_dir(project_id) / f"{document_id}.json"
        if not doc_path.exists():
            return None
            
        with open(doc_path, "r") as f:
            data = json.load(f)
            return DocumentModel(**data)

    def delete_document(self, project_id: str, document_id: str) -> bool:
        """Delete a document and its uploaded file."""
        doc = self.get_document(project_id, document_id)
        if not doc:
            return False

        # Delete JSON metadata
        doc_path = self._get_knowledge_dir(project_id) / f"{document_id}.json"
        if doc_path.exists():
            doc_path.unlink()

        # Delete physical file
        file_path = Path(doc.file_path)
        if file_path.exists():
            file_path.unlink()

        return True

knowledge_service = KnowledgeService()
