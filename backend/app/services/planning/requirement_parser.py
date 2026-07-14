from app.schemas.planning.requirements import StructuredRequirements
from app.services.ai.ai_service import ai_service

class RequirementParser:
    """
    Parses unstructured project context into a structured list of software requirements.
    """

    def parse(self, project_context: str) -> StructuredRequirements:
        return ai_service.generate_structured(
            task="requirement_parsing",
            schema_class=StructuredRequirements,
            context_kwargs={"project_context": project_context}
        )

requirement_parser = RequirementParser()
