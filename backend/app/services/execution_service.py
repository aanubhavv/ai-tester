import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from app.models.execution_models import ExecutionModel, ExecutionStatus
from app.schemas.execution import ExecutionCreate
from app.services.project_service import PROJECTS_ROOT

class ExecutionService:
    """
    Service for managing Executions.
    Executions are stored as JSON files within their respective directories
    under `projects/<project_id>/executions/<execution_id>/`.
    """

    def _get_execution_dir(self, project_id: str, execution_id: str) -> Path:
        return PROJECTS_ROOT / project_id / "executions" / execution_id

    def _get_execution_file(self, project_id: str, execution_id: str) -> Path:
        return self._get_execution_dir(project_id, execution_id) / "execution.json"

    def create_execution(self, data: ExecutionCreate) -> ExecutionModel:
        """Create a new execution."""
        execution = ExecutionModel(
            project_id=data.project_id,
            type=data.type,
            metadata=data.metadata
        )
        
        exec_dir = self._get_execution_dir(execution.project_id, execution.execution_id)
        exec_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for artifacts specific to this execution
        (exec_dir / "artifacts").mkdir(exist_ok=True)
        
        self.save_execution(execution)
        return execution

    def save_execution(self, execution: ExecutionModel):
        """Save execution state to disk."""
        exec_file = self._get_execution_file(execution.project_id, execution.execution_id)
        with open(exec_file, "w") as f:
            f.write(execution.model_dump_json(indent=2))

    def get_execution(self, project_id: str, execution_id: str) -> Optional[ExecutionModel]:
        """Retrieve an execution by ID."""
        exec_file = self._get_execution_file(project_id, execution_id)
        if not exec_file.exists():
            return None
            
        with open(exec_file, "r") as f:
            data = json.load(f)
            return ExecutionModel(**data)

    def list_executions(self, project_id: str) -> List[ExecutionModel]:
        """List all executions for a project."""
        executions_dir = PROJECTS_ROOT / project_id / "executions"
        executions = []
        if not executions_dir.exists():
            return executions
            
        for entry in executions_dir.iterdir():
            if entry.is_dir():
                exec_file = entry / "execution.json"
                if exec_file.exists():
                    try:
                        with open(exec_file, "r") as f:
                            data = json.load(f)
                            executions.append(ExecutionModel(**data))
                    except Exception as e:
                        print(f"Error loading execution from {exec_file}: {e}")
                        
        # Sort by started_at descending
        executions.sort(key=lambda e: e.started_at, reverse=True)
        return executions

    def update_status(self, project_id: str, execution_id: str, status: ExecutionStatus) -> Optional[ExecutionModel]:
        """Update the status of an execution."""
        execution = self.get_execution(project_id, execution_id)
        if not execution:
            return None
            
        execution.status = status
        if status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED):
            execution.completed_at = datetime.utcnow()
            
        self.save_execution(execution)
        return execution

# Global instance
execution_service = ExecutionService()
