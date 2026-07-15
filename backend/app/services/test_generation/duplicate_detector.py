from typing import List, Tuple
from app.schemas.test_cases.models import TestCase

class DuplicateDetector:
    def detect_duplicates(self, test_cases: List[TestCase], threshold: float = 0.85) -> List[Tuple[str, str, float]]:
        # Disabled due to 13-column schema change
        return []

duplicate_detector = DuplicateDetector()
