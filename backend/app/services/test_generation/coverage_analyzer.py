from typing import List, Set
from app.schemas.test_cases.models import TestCase, CoverageReport
from app.schemas.planning.requirements import StructuredRequirements
from app.schemas.planning.features import FeatureExtractionResult

class CoverageAnalyzer:
    """
    Analyzes the traceability mapping of test cases against raw requirements and features
    to identify testing gaps and calculate coverage.
    """

    def analyze(
        self, 
        test_cases: List[TestCase], 
        requirements: StructuredRequirements, 
        features: FeatureExtractionResult
    ) -> CoverageReport:
        
        all_req_ids = {req.id for req in requirements.requirements}
        all_feature_names = {f.name for f in features.features}
        
        covered_req_ids: Set[str] = set()
        covered_features: Set[str] = set()
        
        for tc in test_cases:
            covered_req_ids.update(tc.traceability.requirement_ids)
            covered_features.add(tc.traceability.feature_name)
            
        untested_reqs = list(all_req_ids - covered_req_ids)
        untested_features = list(all_feature_names - covered_features)
        
        warning = None
        if untested_features:
            warning = f"Warning: {len(untested_features)} features have no test cases generated."
            
        return CoverageReport(
            total_requirements=len(all_req_ids),
            covered_requirements=len(covered_req_ids),
            untested_requirement_ids=untested_reqs,
            total_features=len(all_feature_names),
            untested_features=untested_features,
            high_risk_coverage_warning=warning
        )

coverage_analyzer = CoverageAnalyzer()
