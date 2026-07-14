import csv
import io
from typing import List
from app.schemas.test_cases.models import TestCase

class ExportService:
    """
    Exports Test Cases to standard formats (CSV, JSON).
    (XLSX support can be added later by extending this service with openpyxl/pandas).
    """

    def export_to_csv(self, test_cases: List[TestCase]) -> str:
        """
        Returns a CSV string representation of the test cases.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "ID", "Version", "Status", "Priority", "Type", "Feature", "Suite", 
            "Title", "Description", "Requirements", "Preconditions", "Steps", "Postconditions"
        ])
        
        for tc in test_cases:
            # Format steps nicely
            steps_str = "\n".join([f"{s.step_number}. {s.action} -> {s.expected_result}" for s in tc.steps])
            reqs_str = ", ".join(tc.traceability.requirement_ids)
            
            writer.writerow([
                tc.id,
                tc.version,
                tc.status.value,
                tc.priority.value,
                tc.type.value,
                tc.traceability.feature_name,
                tc.traceability.test_suite_name,
                tc.title,
                tc.description,
                reqs_str,
                tc.preconditions,
                steps_str,
                tc.postconditions
            ])
            
        return output.getvalue()

export_service = ExportService()
