from app.schemas.planning.requirements import StructuredRequirements
from app.schemas.planning.features import FeatureExtractionResult
from app.services.planning.llm_client import llm_client

class FeatureExtractor:
    """
    Analyzes structured requirements and deduces the logical product features.
    """

    def extract(self, requirements: StructuredRequirements) -> FeatureExtractionResult:
        req_json = requirements.model_dump_json(indent=2)
        
        prompt = f"""
You are an expert Software Product Architect.
Your task is to analyze the following structured requirements and extract a definitive list of high-level Product Features.

Rules:
1. Deduce logical features that group related requirements. (e.g., "User Authentication", "Checkout Flow").
2. Provide a clear description for each feature.
3. Map the requirement IDs that belong to each feature.
4. Ensure the features represent testable areas of the application.

Requirements:
{req_json}

Output the data matching the requested JSON schema.
"""
        return llm_client.generate_structured(prompt, FeatureExtractionResult)

feature_extractor = FeatureExtractor()
