from pydantic import BaseModel, Field

class TestingStrategy(BaseModel):
    feature_name: str = Field(description="The feature this strategy applies to")
    recommended_strategies: list[str] = Field(
        description="Types of testing (e.g., 'Smoke Testing', 'Visual Regression', 'Boundary Testing')"
    )
    justification: str = Field(description="Why these strategies are recommended for this feature")

class TestSuiteDefinition(BaseModel):
    suite_name: str = Field(description="Name of the test suite (e.g., 'Authentication')")
    feature_name: str = Field(description="The feature this suite tests")
    description: str = Field(description="What this suite covers at a high level")
    high_level_test_cases: list[str] = Field(
        description="List of high-level scenarios (e.g., 'Login with invalid credentials')"
    )

class StrategyGenerationResult(BaseModel):
    strategies: list[TestingStrategy] = Field(
        description="Recommended testing strategies per feature"
    )

class SuiteGenerationResult(BaseModel):
    suites: list[TestSuiteDefinition] = Field(
        description="Logical test suites and their high-level scenarios"
    )
