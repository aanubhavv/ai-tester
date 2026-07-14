import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.services.project_service import PROJECTS_ROOT
from app.services.ai.ai_service import ai_service
from app.schemas.planning.strategy import SuiteGenerationResult
from app.schemas.test_cases.models import TestCase, TestCaseGenerationResult, Traceability

class GenerationService:
    """
    Orchestrates the AI generation of Test Cases based on Test Suites.
    Generates tests suite-by-suite to maintain token efficiency and focus.
    """

    def _get_project_dir(self, project_id: str) -> Path:
        return PROJECTS_ROOT / project_id

    def generate_for_suite(
        self, 
        project_id: str, 
        suite_name: str, 
        feature_name: str, 
        high_level_scenarios: List[str],
        related_requirements: str,
        risk_context: str
    ) -> List[TestCase]:
        """
        Calls the AI Service to generate detailed test cases for a single suite.
        """
        
        scenarios_str = "\n".join([f"- {s}" for s in high_level_scenarios])
        
        result: TestCaseGenerationResult = ai_service.generate_structured(
            task="test_case_generation",
            schema_class=TestCaseGenerationResult,
            context_kwargs={
                "feature_name": feature_name,
                "suite_name": suite_name,
                "high_level_scenarios": scenarios_str,
                "related_requirements": related_requirements,
                "risk_context": risk_context
            }
        )
        
        # Enforce traceability just in case the AI hallucinates
        for tc in result.test_cases:
            tc.traceability.feature_name = feature_name
            tc.traceability.test_suite_name = suite_name
            
        return result.test_cases

    def generate_direct(
        self,
        project_id: str,
        project_context: str,
        docs_content: str
    ) -> List[TestCase]:
        """
        Calls the AI Service to generate detailed test cases directly from context.
        """
        result: TestCaseGenerationResult = ai_service.generate_structured(
            task="test_case_generation_direct",
            schema_class=TestCaseGenerationResult,
            context_kwargs={
                "group": "test_generation",
                "project_context": project_context,
                "docs_content": docs_content
            }
        )
        
        # Enforce default traceability
        for tc in result.test_cases:
            tc.traceability.feature_name = "Direct Generation"
            tc.traceability.test_suite_name = "Project Suite"
            
        return result.test_cases

    def save_test_cases(self, project_id: str, test_cases: List[TestCase]):
        """
        Persists the generated test cases to the project's data directory.
        Appends to existing or creates new.
        """
        tests_dir = self._get_project_dir(project_id) / "test_cases"
        tests_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = tests_dir / "test_cases.json"
        
        existing_cases = self.get_test_cases(project_id)
        
        # Merge new cases, avoiding exact ID duplicates
        existing_ids = {tc.id for tc in existing_cases}
        for tc in test_cases:
            if tc.id not in existing_ids:
                existing_cases.append(tc)
                
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump([tc.model_dump() for tc in existing_cases], f, indent=2)

    def get_test_cases(self, project_id: str) -> List[TestCase]:
        """Loads all test cases for a project."""
        file_path = self._get_project_dir(project_id) / "test_cases" / "test_cases.json"
        if not file_path.exists():
            return []
            
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [TestCase(**tc) for tc in data]

generation_service = GenerationService()
