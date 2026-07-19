import json
import re
import uuid
from typing import List, Dict, Any, Optional

from app.services.ai.ai_service import ai_service
from app.schemas.test_cases.models import TestCase
from app.db.mongodb import get_database

class GenerationService:
    """
    Orchestrates the AI generation of Test Cases based on Test Suites.
    Generates test cases using the custom generation.md prompt and saves to MongoDB.
    """

    @property
    def _collection(self):
        return get_database()["test_cases"]

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
        
        full_context = f"{project_context}\n\n{docs_content}"

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
        
        test_cases = self._parse_markdown_table(raw_markdown)
        return test_cases

    def _parse_markdown_table(self, markdown_text: str) -> List[TestCase]:
        test_cases = []
        lines = markdown_text.strip().split('\n')
        
        in_table = False
        headers_found = False
        for line in lines:
            line = line.strip()
            if not line.startswith('|') or not line.endswith('|'):
                if in_table:
                    break
                continue
            
            in_table = True
            
            if not headers_found:
                if '---' in line:
                    headers_found = True
                continue
                
            cols = [col.strip() for col in line.split('|')[1:-1]]
            
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

    async def save_test_cases(self, project_id: str, test_cases: List[TestCase]):
        """
        Persists the generated test cases to MongoDB.
        Replaces existing test cases for this project for simplicity.
        """
        await self._collection.delete_many({"project_id": project_id})
        
        if test_cases:
            docs = []
            for tc in test_cases:
                doc = tc.model_dump()
                doc["project_id"] = project_id
                docs.append(doc)
            await self._collection.insert_many(docs)

    async def update_test_case_in_db(self, project_id: str, tc_id: str, updates: dict):
        """Atomically updates specific fields of a test case in MongoDB."""
        if not updates:
            return
        await self._collection.update_one(
            {"project_id": project_id, "id": tc_id},
            {"$set": updates}
        )

    async def get_test_cases(self, project_id: str) -> List[TestCase]:
        """Loads all test cases for a project."""
        cursor = self._collection.find({"project_id": project_id})
        docs = await cursor.to_list(length=None)
        return [TestCase(**doc) for doc in docs]

generation_service = GenerationService()
