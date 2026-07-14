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
        "flow_analysis": TaskConfiguration(
            provider=AIProviderType.OPENROUTER,
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            temperature=0.3
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
        "test_case_generation": TaskConfiguration(
            provider=AIProviderType.OPENROUTER,
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            temperature=0.2
        ),
        # A test task used for development
        "health_check": TaskConfiguration(
            provider=AIProviderType.OPENROUTER,
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            temperature=0.0
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
