from pydantic import BaseModel, Field

class UserFlowStep(BaseModel):
    step_number: int
    action: str = Field(description="The action taken in this step (e.g., 'Click Checkout')")
    description: str = Field(description="Details of what happens in this step")

class UserFlow(BaseModel):
    name: str = Field(description="Name of the workflow (e.g., 'Guest Checkout')")
    feature_name: str = Field(description="The primary feature this flow belongs to, if any")
    steps: list[UserFlowStep] = Field(description="Ordered steps to complete the workflow")
    business_value: str = Field(description="Why this flow matters to the business")

class FlowExtractionResult(BaseModel):
    user_flows: list[UserFlow] = Field(
        description="List of business-critical workflows identified from the project knowledge"
    )
