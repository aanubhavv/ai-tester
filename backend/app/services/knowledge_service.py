import io
from typing import List, Optional

from fastapi import UploadFile
import pypdf

from app.models.knowledge_models import DocumentModel, DocumentType, generate_document_id
from app.services.project_service import project_service
from app.db.mongodb import get_database

class KnowledgeService:
    """
    Service for managing Project Knowledge Documents using MongoDB and Cloudinary.
    """

    @property
    def _collection(self):
        return get_database()["knowledge_documents"]

    async def upload_document(
        self, 
        project_id: str, 
        file: UploadFile, 
        title: str, 
        description: str = "",
        document_type: DocumentType = DocumentType.OTHER
    ) -> Optional[DocumentModel]:
        """Upload a file to Cloudinary and store metadata/text in MongoDB."""
        project = await project_service.get_project(project_id)
        if not project:
            return None

        doc_id = generate_document_id()
        filename = file.filename or f"upload_{doc_id}"
        
        file_bytes = await file.read()
        
        # Extract text if PDF
        extracted_text = ""
        if filename.lower().endswith(".pdf"):
            try:
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + "\n"
            except Exception as e:
                print(f"Error extracting PDF: {e}")
        else:
            # Try to decode as text if not PDF
            try:
                extracted_text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                pass

        # Store file in MongoDB directly to avoid Cloudinary PDF strict delivery blocking
        file_url = None
        file_data = file_bytes

        doc = DocumentModel(
            document_id=doc_id,
            project_id=project_id,
            title=title or filename,
            description=description,
            document_type=document_type,
            filename=filename,
            file_url=file_url,
            file_data=file_data,
            content=extracted_text
        )

        await self._collection.insert_one(doc.model_dump())
        return doc

    async def list_documents(self, project_id: str) -> List[DocumentModel]:
        """List all knowledge documents for a project."""
        cursor = self._collection.find(
            {"project_id": project_id},
            projection={"file_data": 0}
        ).sort("uploaded_at", -1)
        docs = await cursor.to_list(length=None)
        return [DocumentModel(**doc) for doc in docs]

    async def get_document(self, project_id: str, document_id: str) -> Optional[DocumentModel]:
        """Get metadata for a specific document."""
        doc = await self._collection.find_one({"project_id": project_id, "document_id": document_id})
        if doc:
            return DocumentModel(**doc)
        return None

    async def get_document_content(self, project_id: str, document_id: str) -> Optional[str]:
        """Get the raw text content of a document."""
        doc = await self.get_document(project_id, document_id)
        if not doc:
            return None
        return doc.content

    async def delete_document(self, project_id: str, document_id: str) -> bool:
        """Delete a document from MongoDB and Cloudinary."""
        doc = await self.get_document(project_id, document_id)
        if not doc:
            return False

        # No longer deleting from Cloudinary since we store directly in MongoDB

        # Delete from MongoDB
        result = await self._collection.delete_one({"project_id": project_id, "document_id": document_id})
        return result.deleted_count > 0

knowledge_service = KnowledgeService()
