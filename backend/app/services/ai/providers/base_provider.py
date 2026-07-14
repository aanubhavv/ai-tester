from abc import ABC, abstractmethod
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel

from app.schemas.ai import AIResponseContext, AIRequestOptions

T = TypeVar('T', bound=BaseModel)

class BaseProvider(ABC):
    """
    The interface that all AI Providers must implement.
    Ensures the rest of the application can remain entirely provider-agnostic.
    """

    @abstractmethod
    def generate_structured(
        self, 
        prompt: str, 
        schema_class: Type[T],
        model: str,
        options: Optional[AIRequestOptions] = None
    ) -> AIResponseContext:
        """
        Generates structured JSON matching the provided Pydantic schema.
        Must return the parsed data and usage metrics wrapped in AIResponseContext.
        """
        pass

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        model: str,
        options: Optional[AIRequestOptions] = None
    ) -> AIResponseContext:
        """
        Generates raw text.
        Must return the text string and usage metrics wrapped in AIResponseContext.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Verifies that the provider is configured correctly and reachable.
        """
        pass
