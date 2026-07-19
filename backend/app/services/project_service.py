import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from app.models.project_models import ProjectModel
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.db.mongodb import get_database

logger = logging.getLogger(__name__)


class ProjectService:
    """
    Service for managing Projects using MongoDB.
    """
    
    @property
    def collection(self):
        return get_database()["projects"]

    async def create_project(self, data: ProjectCreate) -> ProjectModel:
        """Create a new project."""
        project = ProjectModel(
            name=data.name,
            description=data.description or "",
            primary_url=data.primary_url or "",
            max_crawl_pages=data.max_crawl_pages or 5
        )
        
        project_dict = project.model_dump()
        await self.collection.insert_one(project_dict)
        return project

    async def get_project(self, project_id: str) -> Optional[ProjectModel]:
        """Retrieve a project by ID."""
        data = await self.collection.find_one({"project_id": project_id})
        if not data:
            return None
        return ProjectModel(**data)

    async def list_projects(self) -> List[ProjectModel]:
        """List all projects."""
        cursor = self.collection.find({}).sort("updated_at", -1)
        projects = []
        async for doc in cursor:
            projects.append(ProjectModel(**doc))
        return projects

    async def update_project(self, project_id: str, data: ProjectUpdate) -> Optional[ProjectModel]:
        """Update an existing project."""
        project = await self.get_project(project_id)
        if not project:
            return None
            
        update_data = data.model_dump(exclude_unset=True)
        if "project_context" in update_data:
            context_val = update_data.pop("project_context")
            await self.set_project_context(project_id, context_val)

        if not update_data and "project_context" not in data.model_dump(exclude_unset=True):
            return project
            
        for key, value in update_data.items():
            setattr(project, key, value)
            
        project.updated_at = datetime.utcnow()
        
        await self.collection.update_one(
            {"project_id": project_id},
            {"$set": project.model_dump()}
        )
            
        return project

    async def get_project_context(self, project_id: str) -> str:
        """Get the project context from MongoDB."""
        doc = await self.collection.find_one({"project_id": project_id}, {"project_context": 1})
        if doc and "project_context" in doc:
            return doc["project_context"]
        return ""

    async def set_project_context(self, project_id: str, context: str):
        """Set the project context in MongoDB."""
        await self.collection.update_one(
            {"project_id": project_id},
            {"$set": {"project_context": context}},
            upsert=True
        )

    async def delete_project(self, project_id: str) -> bool:
        """Delete a project from MongoDB."""
        result = await self.collection.delete_one({"project_id": project_id})
        return result.deleted_count > 0

# Global instance
project_service = ProjectService()
