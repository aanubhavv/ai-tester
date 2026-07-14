from app.schemas.planning.features import FeatureExtractionResult
from app.schemas.planning.risks import RiskAnalysisResult
from app.schemas.planning.strategy import StrategyGenerationResult
from app.services.planning.llm_client import llm_client

class StrategyGenerator:
    """
    Generates a testing strategy recommendation for each feature based on its risk profile.
    """

    def generate(self, features: FeatureExtractionResult, risks: RiskAnalysisResult) -> StrategyGenerationResult:
        features_json = features.model_dump_json(indent=2)
        risks_json = risks.model_dump_json(indent=2)
        
        prompt = f"""
You are an expert QA Architect.
Your task is to define the optimal Testing Strategy for each feature based on its description and assigned risk level.

Rules:
1. Suggest 2-4 appropriate testing methodologies (e.g., 'Smoke Testing', 'Visual Regression', 'Boundary Testing', 'Accessibility') for each feature.
2. Provide a clear justification for why these strategies are recommended, referencing the feature's risk.
3. Ensure every feature from the provided list receives a strategy.

Features:
{features_json}

Risk Matrix:
{risks_json}

Output the data matching the requested JSON schema.
"""
        return llm_client.generate_structured(prompt, StrategyGenerationResult)

strategy_generator = StrategyGenerator()
