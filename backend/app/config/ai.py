import os
from typing import Dict
from app.schemas.ai import AIProviderType, TaskConfiguration

class AIConfig:
    """
    Centralized configuration for the AI Foundation.
    In a real app, this might be loaded from a YAML file or database.
    """

    # Global Defaults
    DEFAULT_PROVIDER = AIProviderType.OPENROUTER
    DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
    DEFAULT_TEMPERATURE = 0.2
    
    # Task specific routing overrides
    TASKS: Dict[str, TaskConfiguration] = {
        "requirement_parsing": TaskConfiguration(
            provider=AIProviderType.OPENROUTER,
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            temperature=0.1
        ),
        "feature_extraction": TaskConfiguration(
            provider=AIProviderType.OPENROUTER,
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            temperature=0.2
        ),
        "risk_analysis": TaskConfiguration(
            provider=AIProviderType.OPENROUTER,
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            temperature=0.4
        ),
        "strategy_generation": TaskConfiguration(
            provider=AIProviderType.OPENROUTER,
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            temperature=0.3
        ),
        "suite_generation": TaskConfiguration(
            provider=AIProviderType.OPENROUTER,
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            temperature=0.2
        ),
        "generation": TaskConfiguration(
            provider=AIProviderType.OPENROUTER,
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            temperature=0.2
        ),
        "test_generation/exploration_summary": TaskConfiguration(
            provider=AIProviderType.OPENROUTER,
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            temperature=0.2
        ),
        "execution/target_marker": TaskConfiguration(
            provider=AIProviderType.OPENROUTER,
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            temperature=0.2
        ),
        "script_generation/playwright_improvement": TaskConfiguration(
            provider=AIProviderType.OPENROUTER,
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            temperature=0.2
        ),
        "exploration": TaskConfiguration(
            provider=AIProviderType.GEMINI,
            model="gemini-3.1-flash-lite",
            temperature=0.2
        ),
        "script_generation": TaskConfiguration(
            provider=AIProviderType.GEMINI,
            model="gemini-3.1-flash-lite",
            temperature=0.2
        ),
        "self_healing": TaskConfiguration(
            provider=AIProviderType.GEMINI,
            model="gemini-3.1-flash-lite",
            temperature=0.2
        )
    }

    @classmethod
    def get_task_config(cls, task_name: str) -> TaskConfiguration:
        """Returns the configuration for a task, or a generic default if missing."""
        return cls.TASKS.get(
            task_name,
            TaskConfiguration(
                provider=cls.DEFAULT_PROVIDER,
                model=cls.DEFAULT_MODEL,
                temperature=cls.DEFAULT_TEMPERATURE
            )
        )

ai_config = AIConfig()
