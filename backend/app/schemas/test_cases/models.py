from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

class TestCaseStatus(str, Enum):
    DRAFT = "Draft"
    REVIEWED = "Reviewed"
    APPROVED = "Approved"
    DEPRECATED = "Deprecated"

class TestCasePriority(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class TestCaseType(str, Enum):
    SMOKE = "Smoke"
    REGRESSION = "Regression"
    FUNCTIONAL = "Functional"
    NEGATIVE = "Negative"
    BOUNDARY = "Boundary"
    SECURITY = "Security"
    ACCESSIBILITY = "Accessibility"
    PERFORMANCE = "Performance"
    VISUAL = "Visual"

class Traceability(BaseModel):
    """
    Maintains links back to the planning artifacts. Critical for impact analysis.
    """
    requirement_ids: List[str] = Field(default_factory=list, description="IDs of the requirements this test covers.")
    feature_name: str = Field(description="The feature this test belongs to.")
    user_flow_names: List[str] = Field(default_factory=list, description="User flows this test exercises.")
    test_suite_name: str = Field(description="The logical suite this test belongs to.")
    risk_level: Optional[str] = Field(default=None, description="Risk level associated with this test's area.")

class ExecutionProfile(BaseModel):
    """
    Defines HOW a test is run. Decouples the test logic from the execution environment.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(description="e.g., 'Desktop Chrome - Staging', 'Mobile Safari - Prod'")
    browser: Optional[str] = Field(default=None)
    viewport_width: Optional[int] = Field(default=None)
    viewport_height: Optional[int] = Field(default=None)
    environment: str = Field(default="staging")
    locale: Optional[str] = Field(default=None)
    is_authenticated: bool = Field(default=False)

class TestStep(BaseModel):
    step_number: int
    action: str = Field(description="What the user or system does.")
    expected_result: str = Field(description="What should happen after the action.")
    test_data: Optional[str] = Field(default=None, description="Specific data to use during this step.")

class TestCase(BaseModel):
    """
    The core Test Case model. Represents an editable, reviewable QA test in the 13-column format.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique backend ID")
    tc_id: str = Field(description="TC ID (e.g. CHK-001)")
    test_type: str = Field(description="Test Type")
    module_area: str = Field(description="Module/Area")
    title: str = Field(description="Test Case Title")
    severity: str = Field(description="Severity (S0-S3)")
    priority: str = Field(description="Priority (P1-P4)")
    preconditions: str = Field(description="Preconditions")
    test_steps: str = Field(description="Test Steps")
    expected_result: str = Field(description="Expected Result")
    actual_result: str = Field(description="Actual Result")
    status: str = Field(description="Status (Pass/Fail/Blocked/Not Executed)")
    screenshot: str = Field(description="Screenshot (placeholder)")
    remarks: str = Field(description="Remarks")
    
    # Script & Execution
    script: Optional[str] = Field(default=None, description="Generated Playwright script")
    script_status: str = Field(default="Not Generated", description="Not Generated, Generating, Generated, Failed, Outdated, Regenerating")
    execution_status: str = Field(default="Not Executed", description="Not Executed, Queued, Preparing, Running, Passed, Failed, Skipped")
    last_execution_time: Optional[float] = Field(default=None, description="Execution duration in seconds")
    last_execution_timestamp: Optional[str] = Field(default=None, description="ISO timestamp of last execution")
    last_execution_error: Optional[str] = Field(default=None, description="Error message from last failure")
    execution_logs: Optional[str] = Field(default=None, description="Playwright console output")
    script_metadata: Optional[dict] = Field(default=None, description="Metadata about script generation")

    # Audit
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class TestCaseGenerationResult(BaseModel):
    """
    The wrapper model returned by the AI during generation.
    """
    test_cases: List[TestCase] = Field(description="The list of generated test cases.")
    generation_notes: str = Field(description="AI's thoughts on coverage or edge cases considered.")

class CoverageReport(BaseModel):
    """
    Analyzes the gap between requirements/features and generated test cases.
    """
    total_requirements: int
    covered_requirements: int
    untested_requirement_ids: List[str]
    total_features: int
    untested_features: List[str]
    high_risk_coverage_warning: Optional[str] = None
