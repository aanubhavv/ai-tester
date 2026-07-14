from app.schemas.planning.features import FeatureExtractionResult
from app.schemas.planning.flows import FlowExtractionResult
from app.schemas.planning.risks import RiskAnalysisResult
from app.services.ai.ai_service import ai_service

class RiskAnalyzer:
    """
    Assesses the risk level of extracted features and user flows.
    """

    def analyze(self, features: FeatureExtractionResult, flows: FlowExtractionResult) -> RiskAnalysisResult:
        features_json = features.model_dump_json(indent=2)
        flows_json = flows.model_dump_json(indent=2)
        
        return ai_service.generate_structured(
            task="risk_analysis",
            schema_class=RiskAnalysisResult,
            context_kwargs={
                "features_json": features_json,
                "flows_json": flows_json
            }
        )

risk_analyzer = RiskAnalyzer()
