import re
import json
from typing import Type, TypeVar, Any
from pydantic import BaseModel, ValidationError

T = TypeVar('T', bound=BaseModel)

class ResponseParser:
    """
    Safely parses AI responses.
    Some providers (especially when not strictly forcing JSON mode) return 
    markdown wrapped json blocks. This strips them and validates against the schema.
    """

    @staticmethod
    def extract_json_string(text: str) -> str:
        """Strips markdown formatting if present."""
        text = text.strip()
        # Look for markdown code blocks
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            return match.group(1)
        return text

    @staticmethod
    def parse_structured(text: str, schema_class: Type[T]) -> T:
        """
        Extracts JSON from text and validates it against a Pydantic schema.
        """
        clean_text = ResponseParser.extract_json_string(text)
        
        try:
            # First parse as raw JSON to catch standard JSON errors
            data = json.loads(clean_text)
            
            # Then validate with Pydantic
            if isinstance(data, dict):
                return schema_class(**data)
            elif isinstance(data, list):
                # Pydantic models expect dicts. If the AI returned a root list and the schema expects a dict,
                # this will naturally fail via ValidationError, which is intended.
                raise ValueError("Expected JSON object, got JSON array at root level.")
            else:
                raise ValueError("Response is not a valid JSON object.")
                
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to decode JSON from AI response: {e}\nRaw output:\n{clean_text}")
        except ValidationError as e:
            raise ValueError(f"AI response failed schema validation:\n{e.errors()}")

response_parser = ResponseParser()
