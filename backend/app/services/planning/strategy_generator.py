from app.schemas.planning.features import FeatureExtractionResult
from app.schemas.planning.risks import RiskAnalysisResult
from app.schemas.planning.strategy import StrategyGenerationResult
from app.services.ai.ai_service import ai_service

class StrategyGenerator:
    """
    Generates a testing strategy recommendation for each feature based on its risk profile.
    """

    def generate(self, features: FeatureExtractionResult, risks: RiskAnalysisResult) -> StrategyGenerationResult:
        features_json = features.model_dump_json(indent=2)
        risks_json = risks.model_dump_json(indent=2)
        
        return ai_service.generate_structured(
            task="strategy_generation",
            schema_class=StrategyGenerationResult,
            context_kwargs={
                "features_json": features_json,
                "risks_json": risks_json
            }
        )

strategy_generator = StrategyGenerator()
