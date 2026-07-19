from datetime import datetime
from typing import List, Optional

from app.models.execution_models import ExecutionModel, ExecutionStatus
from app.schemas.execution import ExecutionCreate
from app.db.mongodb import get_database

class ExecutionService:
    """
    Service for managing Executions using MongoDB.
    """

    @property
    def collection(self):
        return get_database()["executions"]

    async def create_execution(self, data: ExecutionCreate) -> ExecutionModel:
        """Create a new execution."""
        execution = ExecutionModel(
            project_id=data.project_id,
            type=data.type,
            metadata=data.metadata
        )
        
        await self.collection.insert_one(execution.model_dump())
        return execution

    async def save_execution(self, execution: ExecutionModel):
        """Save execution state to MongoDB."""
        await self.collection.update_one(
            {"execution_id": execution.execution_id},
            {"$set": execution.model_dump()},
            upsert=True
        )

    async def get_execution(self, project_id: str, execution_id: str) -> Optional[ExecutionModel]:
        """Retrieve an execution by ID."""
        data = await self.collection.find_one({
            "project_id": project_id,
            "execution_id": execution_id
        })
        if not data:
            return None
        return ExecutionModel(**data)

    async def list_executions(self, project_id: str) -> List[ExecutionModel]:
        """List all executions for a project."""
        cursor = self.collection.find({"project_id": project_id}).sort("started_at", -1)
        executions = []
        async for doc in cursor:
            executions.append(ExecutionModel(**doc))
        return executions

    async def update_status(self, project_id: str, execution_id: str, status: ExecutionStatus) -> Optional[ExecutionModel]:
        """Update the status of an execution."""
        execution = await self.get_execution(project_id, execution_id)
        if not execution:
            return None
            
        execution.status = status
        if status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED):
            execution.completed_at = datetime.utcnow()
            
        await self.save_execution(execution)
        return execution

# Global instance
execution_service = ExecutionService()
