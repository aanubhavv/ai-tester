from enum import Enum
from pydantic import BaseModel, Field

class RiskLevel(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class RiskAssessment(BaseModel):
    target_name: str = Field(description="Name of the feature or flow being assessed")
    risk_level: RiskLevel
    reasoning: str = Field(description="Why this risk exists")
    business_impact: str = Field(description="The impact if this feature/flow fails")
    suggested_priority: str = Field(description="Suggested testing priority (e.g., P0, P1)")

class RiskAnalysisResult(BaseModel):
    risks: list[RiskAssessment] = Field(description="Risk assessment for all features and flows")
