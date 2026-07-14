from datetime import datetime
from app.schemas.test_cases.models import TestCase

class VersionService:
    """
    Handles bumping versions and maintaining audit trails when test cases are edited.
    """

    def bump_version(self, existing_tc: TestCase, updated_data: dict) -> TestCase:
        """
        Takes an existing TestCase and a dictionary of updates.
        Returns a new TestCase instance with the version bumped.
        """
        # We don't bump version if nothing actually changed, but for simplicity
        # we assume an edit intent means a bump.
        current_data = existing_tc.model_dump()
        
        # Merge updates
        for k, v in updated_data.items():
            if k not in ["id", "version", "created_at", "updated_at"]:
                current_data[k] = v
                
        # Bump version
        current_data["version"] = existing_tc.version + 1
        current_data["updated_at"] = datetime.utcnow().isoformat()
        
        return TestCase(**current_data)

version_service = VersionService()
