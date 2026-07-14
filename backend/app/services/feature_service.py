import json
from pathlib import Path
from typing import List, Optional

from app.models.feature_models import FeatureModel, UserFlowModel, FlowStep
from app.schemas.feature import FeatureCreate, UserFlowCreate
from app.services.project_service import PROJECTS_ROOT, project_service

class FeatureService:
    """
    Service for managing Features and User Flows.
    Features are stored as JSON files in `projects/<project_id>/features/`.
    Flows are stored as JSON files in `projects/<project_id>/flows/`.
    """

    def _get_features_dir(self, project_id: str) -> Path:
        return PROJECTS_ROOT / project_id / "features"

    def _get_flows_dir(self, project_id: str) -> Path:
        return PROJECTS_ROOT / project_id / "flows"

    # --- Features ---

    def create_feature(self, project_id: str, data: FeatureCreate) -> Optional[FeatureModel]:
        project = project_service.get_project(project_id)
        if not project:
            return None

        features_dir = self._get_features_dir(project_id)
        features_dir.mkdir(parents=True, exist_ok=True)

        feature = FeatureModel(
            project_id=project_id,
            name=data.name,
            description=data.description or ""
        )

        feature_path = features_dir / f"{feature.feature_id}.json"
        with open(feature_path, "w") as f:
            f.write(feature.model_dump_json(indent=2))

        return feature

    def get_feature(self, project_id: str, feature_id: str) -> Optional[FeatureModel]:
        feature_path = self._get_features_dir(project_id) / f"{feature_id}.json"
        if not feature_path.exists():
            return None
        with open(feature_path, "r") as f:
            data = json.load(f)
            return FeatureModel(**data)

    def list_features(self, project_id: str) -> List[FeatureModel]:
        features = []
        features_dir = self._get_features_dir(project_id)
        if not features_dir.exists():
            return features

        for entry in features_dir.iterdir():
            if entry.is_file() and entry.suffix == ".json":
                try:
                    with open(entry, "r") as f:
                        data = json.load(f)
                        features.append(FeatureModel(**data))
                except Exception as e:
                    print(f"Error loading feature from {entry}: {e}")

        features.sort(key=lambda f: f.created_at, reverse=True)
        return features

    def delete_feature(self, project_id: str, feature_id: str) -> bool:
        feature_path = self._get_features_dir(project_id) / f"{feature_id}.json"
        if not feature_path.exists():
            return False
        feature_path.unlink()
        return True

    # --- Flows ---

    def create_flow(self, project_id: str, data: UserFlowCreate) -> Optional[UserFlowModel]:
        project = project_service.get_project(project_id)
        if not project:
            return None

        flows_dir = self._get_flows_dir(project_id)
        flows_dir.mkdir(parents=True, exist_ok=True)

        steps = [
            FlowStep(step_number=s.step_number, action=s.action, description=s.description or "")
            for s in data.steps
        ]

        flow = UserFlowModel(
            project_id=project_id,
            feature_id=data.feature_id,
            name=data.name,
            description=data.description or "",
            steps=steps
        )

        flow_path = flows_dir / f"{flow.flow_id}.json"
        with open(flow_path, "w") as f:
            f.write(flow.model_dump_json(indent=2))

        return flow

    def get_flow(self, project_id: str, flow_id: str) -> Optional[UserFlowModel]:
        flow_path = self._get_flows_dir(project_id) / f"{flow_id}.json"
        if not flow_path.exists():
            return None
        with open(flow_path, "r") as f:
            data = json.load(f)
            return UserFlowModel(**data)

    def list_flows(self, project_id: str) -> List[UserFlowModel]:
        flows = []
        flows_dir = self._get_flows_dir(project_id)
        if not flows_dir.exists():
            return flows

        for entry in flows_dir.iterdir():
            if entry.is_file() and entry.suffix == ".json":
                try:
                    with open(entry, "r") as f:
                        data = json.load(f)
                        flows.append(UserFlowModel(**data))
                except Exception as e:
                    print(f"Error loading flow from {entry}: {e}")

        flows.sort(key=lambda f: f.created_at, reverse=True)
        return flows

    def delete_flow(self, project_id: str, flow_id: str) -> bool:
        flow_path = self._get_flows_dir(project_id) / f"{flow_id}.json"
        if not flow_path.exists():
            return False
        flow_path.unlink()
        return True

feature_service = FeatureService()
