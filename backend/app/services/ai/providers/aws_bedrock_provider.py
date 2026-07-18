import time
import json
from typing import Type, Optional, Union
from pydantic import BaseModel
from anthropic import AnthropicBedrock

from app.core.config import settings
from app.schemas.ai import AIResponseContext, AIRequestOptions, AIUsageMetrics, AIProviderType
from app.services.ai.providers.base_provider import BaseProvider

class AWSBedrockProvider(BaseProvider):
    """
    Concrete implementation of BaseProvider for AWS Bedrock using Anthropic models.
    """
    
    def __init__(self):
        kwargs = {}
        if settings.aws_bedrock_api_key:
            kwargs["api_key"] = settings.aws_bedrock_api_key
        
        if settings.aws_access_key_id:
            kwargs["aws_access_key"] = settings.aws_access_key_id
        if settings.aws_secret_access_key:
            kwargs["aws_secret_key"] = settings.aws_secret_access_key
        if settings.aws_session_token:
            kwargs["aws_session_token"] = settings.aws_session_token
        if settings.aws_region_name:
            kwargs["aws_region"] = settings.aws_region_name
            
        self.client = AnthropicBedrock(**kwargs)

    def generate_structured(
        self, 
        prompt: Union[str, list], 
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
        
        # Extract text if prompt is a list (e.g. from multimodal payloads)
        final_prompt = ""
        if isinstance(prompt, list):
            for item in prompt:
                if isinstance(item, str):
                    final_prompt += item + "\n"
        else:
            final_prompt = prompt
            
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temp,
            system=system_prompt,
            messages=[
                {"role": "user", "content": final_prompt}
            ]
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        text_response = response.content[0].text
        
        if not text_response:
            raise ValueError("Received empty response from AWS Bedrock (Anthropic)")
            
        parsed_data = schema_class.model_validate_json(text_response)
        
        prompt_t = response.usage.input_tokens if response.usage else 0
        comp_t = response.usage.output_tokens if response.usage else 0
        total_t = prompt_t + comp_t
        
        metrics = AIUsageMetrics(
            provider=AIProviderType.AWS_BEDROCK,
            model=model,
            prompt_tokens=prompt_t,
            completion_tokens=comp_t,
            total_tokens=total_t,
            estimated_cost_usd=0.0,
            duration_ms=duration_ms
        )
        
        return AIResponseContext(data=parsed_data, metrics=metrics)

    def generate_text(
        self, 
        prompt: Union[str, list], 
        model: str,
        options: Optional[AIRequestOptions] = None
    ) -> AIResponseContext:
        start_time = time.time()
        
        temp = options.temperature if options and options.temperature is not None else 0.2
        max_tokens = options.max_tokens if options and options.max_tokens is not None else 8192
        
        # Extract text if prompt is a list
        final_prompt = ""
        if isinstance(prompt, list):
            for item in prompt:
                if isinstance(item, str):
                    final_prompt += item + "\n"
        else:
            final_prompt = prompt
            
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temp,
            messages=[
                {"role": "user", "content": final_prompt}
            ]
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        text_response = response.content[0].text or ""
        
        prompt_t = response.usage.input_tokens if response.usage else 0
        comp_t = response.usage.output_tokens if response.usage else 0
        total_t = prompt_t + comp_t
        
        metrics = AIUsageMetrics(
            provider=AIProviderType.AWS_BEDROCK,
            model=model,
            prompt_tokens=prompt_t,
            completion_tokens=comp_t,
            total_tokens=total_t,
            estimated_cost_usd=0.0,
            duration_ms=duration_ms
        )
        
        return AIResponseContext(data=text_response, metrics=metrics)

    def health_check(self) -> bool:
        try:
            self.generate_text("Hi", model="anthropic.claude-3-5-haiku-20241022-v1:0", options=AIRequestOptions(max_tokens=10))
            return True
        except Exception:
            return False
