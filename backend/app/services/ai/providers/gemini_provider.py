import time
from typing import Type, Optional
from pydantic import BaseModel
from google import genai
from google.genai import types

from app.core.config import settings

from app.schemas.ai import AIResponseContext, AIRequestOptions, AIUsageMetrics, AIProviderType
from app.services.ai.providers.base_provider import BaseProvider

class GeminiProvider(BaseProvider):
    """
    Concrete implementation of BaseProvider for Google's Gemini models.
    """
    
    def __init__(self):
        self.api_key = settings.gemini_api_key or "dummy_key_for_testing"
        self.client = genai.Client(api_key=self.api_key)

    def _calculate_estimated_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Very rough estimate. In a real system, you'd pull this from a central pricing config.
        e.g., gemini-2.5-flash is ~$0.075 / 1M prompt tokens, $0.30 / 1M completion tokens.
        """
        if "flash" in model.lower():
            return (prompt_tokens / 1_000_000 * 0.075) + (completion_tokens / 1_000_000 * 0.30)
        elif "pro" in model.lower():
            return (prompt_tokens / 1_000_000 * 1.25) + (completion_tokens / 1_000_000 * 5.00)
        return 0.0

    def generate_structured(
        self, 
        prompt: str, 
        schema_class: Type[BaseModel],
        model: str,
        options: Optional[AIRequestOptions] = None
    ) -> AIResponseContext:
        start_time = time.time()
        
        # Merge options
        temp = options.temperature if options and options.temperature is not None else 0.2
        max_tokens = options.max_tokens if options and options.max_tokens is not None else 8192
        
        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema_class,
                temperature=temp,
                max_output_tokens=max_tokens
            ),
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        if not response.text:
            raise ValueError("Received empty response from Gemini")
            
        parsed_data = schema_class.model_validate_json(response.text)
        
        # Usage tracking
        prompt_t = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
        comp_t = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
        total_t = response.usage_metadata.total_token_count if response.usage_metadata else 0
        
        metrics = AIUsageMetrics(
            provider=AIProviderType.GEMINI,
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
        
        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temp,
                max_output_tokens=max_tokens
            ),
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        prompt_t = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
        comp_t = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
        total_t = response.usage_metadata.total_token_count if response.usage_metadata else 0
        
        metrics = AIUsageMetrics(
            provider=AIProviderType.GEMINI,
            model=model,
            prompt_tokens=prompt_t,
            completion_tokens=comp_t,
            total_tokens=total_t,
            estimated_cost_usd=self._calculate_estimated_cost(model, prompt_t, comp_t),
            duration_ms=duration_ms
        )
        
        return AIResponseContext(data=response.text or "", metrics=metrics)

    def health_check(self) -> bool:
        try:
            # A very cheap call to verify API key validity
            self.generate_text("Hi", model="gemini-3.5-flash", options=AIRequestOptions(max_tokens=10))
            return True
        except Exception:
            return False
