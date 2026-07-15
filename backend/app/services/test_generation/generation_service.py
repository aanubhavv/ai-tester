import json
import re
import uuid
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.services.project_service import PROJECTS_ROOT
from app.services.ai.ai_service import ai_service
from app.schemas.test_cases.models import TestCase

class GenerationService:
    """
    Orchestrates the AI generation of Test Cases based on Test Suites.
    Generates test cases using the custom generation.md prompt and exports to Excel.
    """

    def _get_project_dir(self, project_id: str) -> Path:
        return PROJECTS_ROOT / project_id

    def generate_direct(
        self,
        project_id: str,
        project_context: str,
        docs_content: str
    ) -> List[TestCase]:
        """
        Calls the AI Service to generate detailed test cases directly from context,
        parsing the resulting Markdown table into 13 columns.
        """
        
        # Combine project context and docs content for the AI context
        full_context = f"{project_context}\n\n{docs_content}"

        # We use generate_text because the user's prompt instructs the LLM to output a Markdown table
        raw_markdown = ai_service.generate_text(
            task="generation",
            context_kwargs={
                "group": "test_generation",
                "retrieved_context": full_context,
                "module_name": "Full Project",
                "scope_notes": "All modules in context"
            },
            options=None,
            use_cache=False
        )
        
        # Parse the markdown table
        test_cases = self._parse_markdown_table(raw_markdown)
        return test_cases

    def _parse_markdown_table(self, markdown_text: str) -> List[TestCase]:
        test_cases = []
        lines = markdown_text.strip().split('\n')
        
        # Find the start of the table
        in_table = False
        headers_found = False
        for line in lines:
            line = line.strip()
            if not line.startswith('|') or not line.endswith('|'):
                if in_table:
                    # End of table
                    break
                continue
            
            in_table = True
            
            if not headers_found:
                # The first row is headers, second row is separators like |---|---|
                if '---' in line:
                    headers_found = True
                continue
                
            # Split line by | and clean up whitespace
            # Handle escaped pipes if they exist, but split naively for now
            cols = [col.strip() for col in line.split('|')[1:-1]]
            
            # The prompt requests exactly 13 columns
            if len(cols) >= 13:
                tc = TestCase(
                    id=str(uuid.uuid4()),
                    tc_id=cols[0],
                    test_type=cols[1],
                    module_area=cols[2],
                    title=cols[3],
                    severity=cols[4],
                    priority=cols[5],
                    preconditions=cols[6],
                    test_steps=cols[7],
                    expected_result=cols[8],
                    actual_result=cols[9],
                    status=cols[10],
                    screenshot=cols[11],
                    remarks=cols[12]
                )
                test_cases.append(tc)

        return test_cases

    def save_test_cases(self, project_id: str, test_cases: List[TestCase]):
        """
        Persists the generated test cases to the project's data directory.
        Saves as JSON and also as XLSX.
        """
        tests_dir = self._get_project_dir(project_id) / "test_cases"
        tests_dir.mkdir(parents=True, exist_ok=True)
        
        json_path = tests_dir / "test_cases.json"
        xlsx_path = tests_dir / "test_cases.xlsx"
        
        # We replace existing for this implementation to keep it simple and clean
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump([tc.model_dump() for tc in test_cases], f, indent=2)
            
        # Save to XLSX using pandas
        df = pd.DataFrame([tc.model_dump() for tc in test_cases])
        
        # Rename columns to make them nice in Excel
        df.rename(columns={
            "tc_id": "TC ID",
            "test_type": "Test Type",
            "module_area": "Module/Area",
            "title": "Test Case Title",
            "severity": "Severity",
            "priority": "Priority",
            "preconditions": "Preconditions",
            "test_steps": "Test Steps",
            "expected_result": "Expected Result",
            "actual_result": "Actual Result",
            "status": "Status",
            "screenshot": "Screenshot",
            "remarks": "Remarks"
        }, inplace=True)
        
        # Drop internal fields we don't want in Excel
        if 'id' in df.columns:
            df.drop(columns=['id', 'created_at', 'updated_at'], inplace=True, errors='ignore')
            
        df.to_excel(str(xlsx_path), index=False)

    def get_test_cases(self, project_id: str) -> List[TestCase]:
        """Loads all test cases for a project."""
        file_path = self._get_project_dir(project_id) / "test_cases" / "test_cases.json"
        if not file_path.exists():
            return []
            
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [TestCase(**tc) for tc in data]

generation_service = GenerationService()
