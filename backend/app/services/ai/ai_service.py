import logging
from typing import Type, TypeVar, Any, Optional, Union
from pydantic import BaseModel

from app.schemas.ai import AIResponseContext, AIRequestOptions, AIProviderType
from app.services.ai.model_router import model_router
from app.services.ai.provider_manager import provider_manager
from app.services.ai.prompt_manager import prompt_manager
from app.services.ai.retry_handler import retry_handler
from app.services.ai.response_parser import response_parser
from app.services.ai.cost_tracker import cost_tracker
from app.services.ai.cache import ai_cache

T = TypeVar('T', bound=BaseModel)
logger = logging.getLogger(__name__)

class AIService:
    """
    The central Facade for all AI operations in the application.
    Business logic should ONLY interact with this service.
    """

    def generate_structured(
        self, 
        task: str, 
        schema_class: Type[T],
        context_kwargs: dict,
        options: Optional[AIRequestOptions] = None,
        use_cache: bool = True
    ) -> T:
        """
        Executes a task and returns a strongly-typed Pydantic model.
        """
        # 1. Prepare Prompt
        prompt = prompt_manager.get_prompt(task, **context_kwargs)

        # 2. Resolve Routing
        provider, model_name, merged_options = model_router.resolve_routing(task, options)

        # 3. Check Cache
        if use_cache:
            cached_data = ai_cache.get(task, prompt, model_name)
            if cached_data:
                logger.info(f"AI Cache Hit for task '{task}'")
                return schema_class(**cached_data)

        # 4. Define Provider Call (to be wrapped in retry)
        def _execute() -> AIResponseContext:
            return provider.generate_structured(
                prompt=prompt,
                schema_class=schema_class,
                model=model_name,
                options=merged_options
            )

        # 5. Execute with Retry
        response_context: AIResponseContext = retry_handler.execute_with_retry(
            _execute, 
            max_retries=merged_options.retries if merged_options.retries else 3
        )

        # 6. Parse and Ensure Strict Compliance
        # The provider *should* return the parsed Pydantic object, but we defensively 
        # ensure it passes our parser if the provider leaked markdown wrapped json text.
        if isinstance(response_context.data, str):
            final_data = response_parser.parse_structured(response_context.data, schema_class)
        else:
            final_data = response_context.data
            
        # 7. Record Costs
        cost_tracker.record_usage(task, response_context.metrics)

        # 8. Update Cache
        if use_cache:
            ai_cache.set(task, prompt, model_name, final_data.model_dump())

        return final_data

    def generate_structured_raw(
        self,
        prompt: Union[str, list],
        schema_class: Type[T],
        model_name: str = "gemini-3.1-flash-lite",
        provider_type: AIProviderType = AIProviderType.GEMINI,
        options: Optional[AIRequestOptions] = None
    ) -> T:
        """
        Executes a task with a raw prompt (string or list for multimodal) and returns a strongly-typed Pydantic model.
        Bypasses prompt_manager and cache.
        """
        provider = provider_manager.get_provider(provider_type)
        merged_options = options or AIRequestOptions(retries=3)
        if not merged_options.retries:
            merged_options.retries = 3
        
        resolved_model = model_name
            
        def _execute() -> AIResponseContext:
            return provider.generate_structured(
                prompt=prompt,
                schema_class=schema_class,
                model=resolved_model,
                options=merged_options
            )

        response_context: AIResponseContext = retry_handler.execute_with_retry(
            _execute, 
            max_retries=merged_options.retries if merged_options.retries else 3
        )

        if isinstance(response_context.data, str):
            final_data = response_parser.parse_structured(response_context.data, schema_class)
        else:
            final_data = response_context.data
            
        cost_tracker.record_usage("autonomous_agent", response_context.metrics)
        return final_data

    def generate_text(
        self,
        task: str,
        context_kwargs: dict,
        options: Optional[AIRequestOptions] = None,
        use_cache: bool = True
    ) -> str:
        """
        Executes a task and returns raw text.
        """
        prompt = prompt_manager.get_prompt(task, **context_kwargs)
        provider, model_name, merged_options = model_router.resolve_routing(task, options)

        if use_cache:
            cached_data = ai_cache.get(task, prompt, model_name)
            if cached_data:
                logger.info(f"AI Cache Hit for task '{task}'")
                return cached_data

        def _execute() -> AIResponseContext:
            return provider.generate_text(
                prompt=prompt,
                model=model_name,
                options=merged_options
            )

        response_context: AIResponseContext = retry_handler.execute_with_retry(
            _execute, 
            max_retries=merged_options.retries if merged_options.retries else 3
        )

        final_text = str(response_context.data)
        
        cost_tracker.record_usage(task, response_context.metrics)

        if use_cache:
            ai_cache.set(task, prompt, model_name, final_text)

        return final_text

    def generate_text_raw(
        self,
        prompt: Union[str, list],
        model_name: str = "gemini-3.1-flash-lite",
        provider_type: AIProviderType = AIProviderType.GEMINI,
        options: Optional[AIRequestOptions] = None
    ) -> str:
        """
        Executes a task with a raw prompt (string or list for multimodal) and returns raw text.
        Bypasses prompt_manager and cache.
        """
        provider = provider_manager.get_provider(provider_type)
        merged_options = options or AIRequestOptions(retries=3)
        if not merged_options.retries:
            merged_options.retries = 3
        
        def _execute() -> AIResponseContext:
            return provider.generate_text(
                prompt=prompt,
                model=model_name,
                options=merged_options
            )

        response_context: AIResponseContext = retry_handler.execute_with_retry(
            _execute, 
            max_retries=merged_options.retries if merged_options.retries else 3
        )

        final_text = str(response_context.data)
        cost_tracker.record_usage("autonomous_agent_text", response_context.metrics)
        return final_text

ai_service = AIService()
