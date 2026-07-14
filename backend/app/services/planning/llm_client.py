import os
from typing import TypeVar, Type
from pydantic import BaseModel
from google import genai
from google.genai import types

T = TypeVar('T', bound=BaseModel)

class LLMClient:
    """
    Base client for interacting with the Google GenAI SDK.
    Responsible for sending prompts and enforcing Pydantic schema outputs.
    """
    
    def __init__(self):
        # Initialise with API key from environment, or a dummy for local dev/testing
        api_key = os.getenv("GEMINI_API_KEY", "dummy_key_for_testing")
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.5-flash" # Default model

    def generate_structured(self, prompt: str, schema_class: Type[T]) -> T:
        """
        Generates structured JSON matching the provided Pydantic schema.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema_class,
                ),
            )
            
            if not response.text:
                raise ValueError("Received empty response from LLM")
                
            # Parse the JSON text into the Pydantic model
            return schema_class.model_validate_json(response.text)
            
        except Exception as e:
            # In a real app we'd log this properly
            print(f"LLM Generation Error: {e}")
            # For resilience in the prototype, we can return an empty model instance if it's safe,
            # or just re-raise. We'll re-raise for now so the caller knows it failed.
            raise e

llm_client = LLMClient()
