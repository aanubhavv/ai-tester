from typing import List, Dict, Tuple
from app.schemas.test_cases.models import TestCase
import difflib

class DuplicateDetector:
    """
    Identifies potential duplicate test cases based on title and step similarity.
    """

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def detect_duplicates(self, test_cases: List[TestCase], threshold: float = 0.85) -> List[Tuple[str, str, float]]:
        """
        Returns a list of tuples (test_case_1_id, test_case_2_id, similarity_score) 
        for tests that exceed the similarity threshold.
        """
        duplicates = []
        n = len(test_cases)
        
        for i in range(n):
            for j in range(i + 1, n):
                tc1 = test_cases[i]
                tc2 = test_cases[j]
                
                # Combine title and descriptions for a heuristic check
                text1 = tc1.title + " " + tc1.description
                text2 = tc2.title + " " + tc2.description
                
                score = self._calculate_similarity(text1, text2)
                
                if score >= threshold:
                    duplicates.append((tc1.id, tc2.id, round(score, 2)))
                    
        return duplicates

duplicate_detector = DuplicateDetector()
