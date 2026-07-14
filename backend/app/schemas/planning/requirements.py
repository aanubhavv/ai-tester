from pydantic import BaseModel, Field

class RequirementItem(BaseModel):
    id: str = Field(description="A unique identifier for this requirement")
    feature_name: str = Field(description="The high-level feature this requirement belongs to")
    description: str = Field(description="A clear description of the requirement")

class StructuredRequirements(BaseModel):
    requirements: list[RequirementItem] = Field(
        description="A list of normalized, structured requirements extracted from raw text"
    )
