from typing import List
from app.schemas.test_cases.models import TestCase, CoverageReport
from app.schemas.planning.requirements import StructuredRequirements
from app.schemas.planning.features import FeatureExtractionResult

class CoverageAnalyzer:
    def analyze(
        self, 
        test_cases: List[TestCase], 
        requirements: StructuredRequirements, 
        features: FeatureExtractionResult
    ) -> CoverageReport:
        # Disabled due to 13-column schema change
        return CoverageReport(
            total_requirements=0,
            covered_requirements=0,
            untested_requirement_ids=[],
            total_features=0,
            covered_features=0,
            untested_feature_names=[],
            coverage_percentage=0.0
        )

coverage_analyzer = CoverageAnalyzer()
