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
    The core Test Case model. Represents an editable, reviewable QA test.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for the test case.")
    version: int = Field(default=1, description="Version tracking for audit history.")
    title: str = Field(description="A clear, concise title for the test case.")
    description: str = Field(description="A detailed description of the test case's purpose.")
    
    # Classification
    status: TestCaseStatus = Field(default=TestCaseStatus.DRAFT)
    priority: TestCasePriority = Field(default=TestCasePriority.MEDIUM)
    type: TestCaseType = Field(default=TestCaseType.FUNCTIONAL)
    tags: List[str] = Field(default_factory=list)
    
    # Execution Logic
    preconditions: str = Field(default="", description="Setup required before the test can run.")
    steps: List[TestStep] = Field(description="The exact steps to execute the test.")
    postconditions: str = Field(default="", description="Cleanup or assertions after the test finishes.")
    
    # Traceability
    traceability: Traceability
    
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
