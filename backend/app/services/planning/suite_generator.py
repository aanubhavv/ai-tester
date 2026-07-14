from app.schemas.planning.features import FeatureExtractionResult
from app.schemas.planning.strategy import StrategyGenerationResult, SuiteGenerationResult
from app.services.planning.llm_client import llm_client

class SuiteGenerator:
    """
    Generates high-level logical test suites and test cases based on the overall strategy.
    """

    def generate(self, features: FeatureExtractionResult, strategy: StrategyGenerationResult) -> SuiteGenerationResult:
        features_json = features.model_dump_json(indent=2)
        strategy_json = strategy.model_dump_json(indent=2)
        
        prompt = f"""
You are an expert QA Automation Engineer.
Your task is to translate the testing strategy into logical Test Suites containing high-level test scenarios.

Rules:
1. Create Test Suites for the features provided.
2. Under each suite, list 3-5 high-level test cases (e.g., "Login with invalid password", "Checkout with expired card").
3. Ensure these cases align with the recommended testing methodologies for that feature.
4. Do not write automation code, just the names of the logical scenarios.

Features:
{features_json}

Testing Strategy:
{strategy_json}

Output the data matching the requested JSON schema.
"""
        return llm_client.generate_structured(prompt, SuiteGenerationResult)

suite_generator = SuiteGenerator()
