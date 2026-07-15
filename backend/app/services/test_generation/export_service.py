from typing import List
from app.schemas.test_cases.models import TestCase

class ExportService:
    def export_to_csv(self, test_cases: List[TestCase]) -> str:
        return ""

export_service = ExportService()
