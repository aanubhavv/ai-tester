from app.schemas.planning.requirements import StructuredRequirements
from app.services.planning.llm_client import llm_client

class RequirementParser:
    """
    Analyzes raw project context and normalizes it into a list of structured requirements.
    """
    
    def parse(self, project_context: str) -> StructuredRequirements:
        prompt = f"""
You are an expert Business Analyst and QA Architect.
Your task is to analyze the following raw project context and extract all software requirements.

Rules:
1. Normalize the requirements into a structured list.
2. Group them under a logical 'feature_name' (e.g., "Checkout", "Authentication").
3. Ensure descriptions are clear and testable.
4. If the document is not a software PRD (e.g., a resume), extract whatever logical capabilities or responsibilities are described as "requirements".

Context:
{project_context}

Output the data matching the requested JSON schema.
"""
        return llm_client.generate_structured(prompt, StructuredRequirements)

requirement_parser = RequirementParser()
