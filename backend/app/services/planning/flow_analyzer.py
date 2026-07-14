from app.schemas.planning.features import FeatureExtractionResult
from app.schemas.planning.flows import FlowExtractionResult
from app.services.ai.ai_service import ai_service

class FlowAnalyzer:
    """
    Analyzes project context and extracted features to identify business-critical user journeys.
    """

    def analyze(self, project_context: str, features: FeatureExtractionResult) -> FlowExtractionResult:
        features_json = features.model_dump_json(indent=2)
        
        return ai_service.generate_structured(
            task="flow_analysis",
            schema_class=FlowExtractionResult,
            context_kwargs={
                "features_json": features_json,
                "project_context": project_context
            }
        )

flow_analyzer = FlowAnalyzer()
