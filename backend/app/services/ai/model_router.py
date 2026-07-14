from typing import Tuple, Optional
from app.config.ai import ai_config
from app.schemas.ai import AIRequestOptions, TaskConfiguration
from app.services.ai.providers.base_provider import BaseProvider
from app.services.ai.provider_manager import provider_manager

class ModelRouter:
    """
    Decides which provider and model to use for a specific task.
    """

    def resolve_routing(self, task_name: str, options_override: Optional[AIRequestOptions] = None) -> Tuple[BaseProvider, str, AIRequestOptions]:
        """
        Looks up the task in the central configuration.
        Returns the concrete Provider instance, the model string, and the merged execution options.
        """
        # 1. Look up task config
        task_config: TaskConfiguration = ai_config.get_task_config(task_name)
        
        # 2. Get Provider
        provider = provider_manager.get_provider(task_config.provider)
        
        # 3. Merge Options
        # Overrides take precedence over task defaults
        merged_options = AIRequestOptions(
            temperature=options_override.temperature if options_override and options_override.temperature is not None else task_config.temperature,
            max_tokens=options_override.max_tokens if options_override and options_override.max_tokens is not None else task_config.max_tokens,
            retries=options_override.retries if options_override and options_override.retries is not None else task_config.retries,
            timeout=options_override.timeout if options_override and options_override.timeout is not None else task_config.timeout
        )
        
        return provider, task_config.model, merged_options

model_router = ModelRouter()
