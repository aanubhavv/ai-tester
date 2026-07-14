from pydantic import BaseModel, Field

class ExtractedFeature(BaseModel):
    name: str = Field(description="Name of the logical product feature")
    description: str = Field(description="A brief description of what this feature does")
    related_requirements: list[str] = Field(
        description="IDs of the requirements that this feature satisfies"
    )

class FeatureExtractionResult(BaseModel):
    features: list[ExtractedFeature] = Field(
        description="List of all distinct logical product features deduced from the requirements"
    )
