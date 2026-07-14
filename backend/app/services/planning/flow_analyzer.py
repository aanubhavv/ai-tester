from app.schemas.planning.features import FeatureExtractionResult
from app.schemas.planning.flows import FlowExtractionResult
from app.services.planning.llm_client import llm_client

class FlowAnalyzer:
    """
    Analyzes project context and extracted features to identify business-critical user journeys.
    """

    def analyze(self, project_context: str, features: FeatureExtractionResult) -> FlowExtractionResult:
        features_json = features.model_dump_json(indent=2)
        
        prompt = f"""
You are an expert QA Architect.
Your task is to identify the most critical user workflows (User Flows) based on the project context and the extracted features.

Rules:
1. A User Flow is a sequence of actions a user takes to achieve a goal.
2. Break down each flow into distinct, numbered steps.
3. Link the flow to a primary feature from the provided list if applicable.
4. Explain the 'business_value' of this flow (e.g., "Generates revenue", "Retains users").

Extracted Features:
{features_json}

Raw Project Context:
{project_context}

Output the data matching the requested JSON schema.
"""
        return llm_client.generate_structured(prompt, FlowExtractionResult)

flow_analyzer = FlowAnalyzer()
