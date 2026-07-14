from app.schemas.planning.features import FeatureExtractionResult
from app.schemas.planning.strategy import StrategyGenerationResult, SuiteGenerationResult
from app.services.ai.ai_service import ai_service

class SuiteGenerator:
    """
    Generates high-level logical test suites and test cases based on the overall strategy.
    """

    def generate(self, features: FeatureExtractionResult, strategy: StrategyGenerationResult) -> SuiteGenerationResult:
        features_json = features.model_dump_json(indent=2)
        strategy_json = strategy.model_dump_json(indent=2)
        
        return ai_service.generate_structured(
            task="suite_generation",
            schema_class=SuiteGenerationResult,
            context_kwargs={
                "features_json": features_json,
                "strategy_json": strategy_json
            }
        )

suite_generator = SuiteGenerator()
