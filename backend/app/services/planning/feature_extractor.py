from app.schemas.planning.requirements import StructuredRequirements
from app.schemas.planning.features import FeatureExtractionResult
from app.services.ai.ai_service import ai_service

class FeatureExtractor:
    """
    Extracts high-level logical features from the parsed requirements.
    """

    def extract(self, requirements: StructuredRequirements) -> FeatureExtractionResult:
        requirements_json = requirements.model_dump_json(indent=2)
        
        return ai_service.generate_structured(
            task="feature_extraction",
            schema_class=FeatureExtractionResult,
            context_kwargs={"requirements_json": requirements_json}
        )

feature_extractor = FeatureExtractor()
