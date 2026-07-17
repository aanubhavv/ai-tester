import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from app.models.project_models import ProjectModel
from app.schemas.project import ProjectCreate, ProjectUpdate

PROJECTS_ROOT = Path("projects")

class ProjectService:
    """
    Service for managing Projects.
    Projects are stored as JSON files within their respective directories
    under the `projects/` root directory.
    """

    def __init__(self):
        # Ensure the root projects directory exists
        PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)

    def _get_project_dir(self, project_id: str) -> Path:
        return PROJECTS_ROOT / project_id

    def _get_project_file(self, project_id: str) -> Path:
        return self._get_project_dir(project_id) / "project.json"

    def _init_project_structure(self, project_id: str):
        """Creates the directory structure for a new project."""
        base_dir = self._get_project_dir(project_id)
        base_dir.mkdir(parents=True, exist_ok=True)
        (base_dir / "knowledge").mkdir(exist_ok=True)
        (base_dir / "test_cases").mkdir(exist_ok=True)
        (base_dir / "executions").mkdir(exist_ok=True)

    def create_project(self, data: ProjectCreate) -> ProjectModel:
        """Create a new project."""
        project = ProjectModel(
            name=data.name,
            description=data.description or "",
            primary_url=data.primary_url or "",
            max_crawl_pages=data.max_crawl_pages or 5
        )
        
        self._init_project_structure(project.project_id)
        
        project_file = self._get_project_file(project.project_id)
        with open(project_file, "w") as f:
            f.write(project.model_dump_json(indent=2))
            
        return project

    def get_project(self, project_id: str) -> Optional[ProjectModel]:
        """Retrieve a project by ID."""
        project_file = self._get_project_file(project_id)
        if not project_file.exists():
            return None
            
        with open(project_file, "r") as f:
            data = json.load(f)
            return ProjectModel(**data)

    def list_projects(self) -> List[ProjectModel]:
        """List all projects."""
        projects = []
        if not PROJECTS_ROOT.exists():
            return projects
            
        for entry in os.scandir(PROJECTS_ROOT):
            if entry.is_dir() and not entry.name.startswith("."):
                project_file = Path(entry.path) / "project.json"
                if project_file.exists():
                    try:
                        with open(project_file, "r") as f:
                            data = json.load(f)
                            projects.append(ProjectModel(**data))
                    except Exception as e:
                        print(f"Error loading project from {project_file}: {e}")
                        
        # Sort by updated_at descending
        projects.sort(key=lambda p: p.updated_at, reverse=True)
        return projects

    def update_project(self, project_id: str, data: ProjectUpdate) -> Optional[ProjectModel]:
        """Update an existing project."""
        project = self.get_project(project_id)
        if not project:
            return None
            
        update_data = data.model_dump(exclude_unset=True)
        if "project_context" in update_data:
            context_val = update_data.pop("project_context")
            self.set_project_context(project_id, context_val)

        if not update_data and "project_context" not in data.model_dump(exclude_unset=True):
            return project
            
        for key, value in update_data.items():
            setattr(project, key, value)
            
        project.updated_at = datetime.utcnow()
        
        project_file = self._get_project_file(project_id)
        with open(project_file, "w") as f:
            f.write(project.model_dump_json(indent=2))
            
        return project

    def get_project_context(self, project_id: str) -> str:
        context_file = self._get_project_dir(project_id) / "knowledge" / "project_context.md"
        if context_file.exists():
            with open(context_file, "r") as f:
                return f.read()
        return ""

    def set_project_context(self, project_id: str, context: str):
        context_file = self._get_project_dir(project_id) / "knowledge" / "project_context.md"
        with open(context_file, "w") as f:
            f.write(context)

    def delete_project(self, project_id: str) -> bool:
        """
        Delete a project. 
        Note: Currently we will only support deleting the project.json.
        Full recursive deletion of directories can be dangerous.
        We'll rename the directory to .deleted_<id> instead of rm -rf.
        """
        project_dir = self._get_project_dir(project_id)
        if not project_dir.exists():
            return False
            
        deleted_dir = PROJECTS_ROOT / f".deleted_{project_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            project_dir.rename(deleted_dir)
            return True
        except Exception as e:
            print(f"Failed to delete/rename project dir: {e}")
            return False

# Global instance
project_service = ProjectService()
