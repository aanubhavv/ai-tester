import time
import json
from typing import Type, Optional
from pydantic import BaseModel
from openai import OpenAI

from app.core.config import settings
from app.schemas.ai import AIResponseContext, AIRequestOptions, AIUsageMetrics, AIProviderType
from app.services.ai.providers.base_provider import BaseProvider

class OpenRouterProvider(BaseProvider):
    """
    Concrete implementation of BaseProvider for OpenRouter.
    """
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key or "dummy_key_for_testing"
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )

    def _calculate_estimated_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        OpenRouter returns the actual cost in the API response headers or usage sometimes, 
        but we can just estimate or return 0 for now as it's complex to track for all models locally.
        """
        return 0.0

    def generate_structured(
        self, 
        prompt: str, 
        schema_class: Type[BaseModel],
        model: str,
        options: Optional[AIRequestOptions] = None
    ) -> AIResponseContext:
        start_time = time.time()
        
        temp = options.temperature if options and options.temperature is not None else 0.2
        max_tokens = options.max_tokens if options and options.max_tokens is not None else 8192
        
        # Append schema instructions to the prompt to ensure JSON response
        schema_json = schema_class.model_json_schema()
        system_prompt = f"You are a helpful assistant. You must respond with raw, valid JSON that matches the following schema:\n{json.dumps(schema_json)}\nDo not wrap the JSON in markdown code blocks."
        
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=temp,
            max_tokens=max_tokens
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        choice = response.choices[0]
        text_response = choice.message.content
        
        if not text_response:
            raise ValueError("Received empty response from OpenRouter")
            
        parsed_data = schema_class.model_validate_json(text_response)
        
        prompt_t = response.usage.prompt_tokens if response.usage else 0
        comp_t = response.usage.completion_tokens if response.usage else 0
        total_t = response.usage.total_tokens if response.usage else 0
        
        metrics = AIUsageMetrics(
            provider=AIProviderType.OPENROUTER,
            model=model,
            prompt_tokens=prompt_t,
            completion_tokens=comp_t,
            total_tokens=total_t,
            estimated_cost_usd=self._calculate_estimated_cost(model, prompt_t, comp_t),
            duration_ms=duration_ms
        )
        
        return AIResponseContext(data=parsed_data, metrics=metrics)

    def generate_text(
        self, 
        prompt: str, 
        model: str,
        options: Optional[AIRequestOptions] = None
    ) -> AIResponseContext:
        start_time = time.time()
        
        temp = options.temperature if options and options.temperature is not None else 0.2
        max_tokens = options.max_tokens if options and options.max_tokens is not None else 8192
        
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=temp,
            max_tokens=max_tokens
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        choice = response.choices[0]
        text_response = choice.message.content or ""
        
        prompt_t = response.usage.prompt_tokens if response.usage else 0
        comp_t = response.usage.completion_tokens if response.usage else 0
        total_t = response.usage.total_tokens if response.usage else 0
        
        metrics = AIUsageMetrics(
            provider=AIProviderType.OPENROUTER,
            model=model,
            prompt_tokens=prompt_t,
            completion_tokens=comp_t,
            total_tokens=total_t,
            estimated_cost_usd=self._calculate_estimated_cost(model, prompt_t, comp_t),
            duration_ms=duration_ms
        )
        
        return AIResponseContext(data=text_response, metrics=metrics)

    def health_check(self) -> bool:
        try:
            self.generate_text("Hi", model="nvidia/nemotron-3-ultra-550b-a55b:free", options=AIRequestOptions(max_tokens=10))
            return True
        except Exception:
            return False
