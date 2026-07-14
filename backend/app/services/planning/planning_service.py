import json
from pathlib import Path
from typing import Optional, Dict, Any

from app.services.project_service import PROJECTS_ROOT, project_service
from app.services.planning.prompt_builder import PromptBuilder
from app.services.planning.requirement_parser import requirement_parser
from app.services.planning.feature_extractor import feature_extractor
from app.services.planning.flow_analyzer import flow_analyzer
from app.services.planning.risk_analyzer import risk_analyzer
from app.services.planning.strategy_generator import strategy_generator
from app.services.planning.suite_generator import suite_generator

class PlanningService:
    """
    Orchestrates the AI Planning Pipeline and persists artifacts.
    """

    def _get_planning_dir(self, project_id: str) -> Path:
        return PROJECTS_ROOT / project_id / "planning"

    def generate_planning(self, project_id: str) -> bool:
        """
        Executes the full planning pipeline and saves all artifacts.
        """
        project = project_service.get_project(project_id)
        if not project:
            return False

        planning_dir = self._get_planning_dir(project_id)
        planning_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Build Context
            context = PromptBuilder.build_project_context(project_id)

            # 2. Parse Requirements
            requirements = requirement_parser.parse(context)
            self._save_artifact(planning_dir, "requirements.json", requirements.model_dump())

            # 3. Extract Features
            features = feature_extractor.extract(requirements)
            self._save_artifact(planning_dir, "features.json", features.model_dump())

            # 4. Analyze User Flows
            flows = flow_analyzer.analyze(context, features)
            self._save_artifact(planning_dir, "user_flows.json", flows.model_dump())

            # 5. Assess Risks
            risks = risk_analyzer.analyze(features, flows)
            self._save_artifact(planning_dir, "risks.json", risks.model_dump())

            # 6. Generate Strategy
            strategy = strategy_generator.generate(features, risks)
            self._save_artifact(planning_dir, "testing_strategy.json", strategy.model_dump())

            # 7. Generate Test Suites
            suites = suite_generator.generate(features, strategy)
            self._save_artifact(planning_dir, "test_suites.json", suites.model_dump())

            return True

        except Exception as e:
            print(f"Error during planning pipeline: {e}")
            return False

    def _save_artifact(self, planning_dir: Path, filename: str, data: dict):
        file_path = planning_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_artifact(self, project_id: str, filename: str) -> Optional[Dict[str, Any]]:
        file_path = self._get_planning_dir(project_id) / filename
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

planning_service = PlanningService()
