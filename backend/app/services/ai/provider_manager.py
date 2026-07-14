from typing import Dict
from app.schemas.ai import AIProviderType
from app.services.ai.providers.base_provider import BaseProvider
from app.services.ai.providers.gemini_provider import GeminiProvider

class ProviderManager:
    """
    Factory for managing and instantiating AI providers.
    """
    
    def __init__(self):
        # Lazy loading cache for providers
        self._providers: Dict[AIProviderType, BaseProvider] = {}

    def get_provider(self, provider_type: AIProviderType) -> BaseProvider:
        """
        Returns a singleton instance of the requested provider.
        Instantiates it on the first request.
        """
        if provider_type in self._providers:
            return self._providers[provider_type]

        if provider_type == AIProviderType.GEMINI:
            provider = GeminiProvider()
            self._providers[provider_type] = provider
            return provider
            
        elif provider_type == AIProviderType.OPENROUTER:
            from app.services.ai.providers.openrouter_provider import OpenRouterProvider
            provider = OpenRouterProvider()
            self._providers[provider_type] = provider
            return provider

        raise NotImplementedError(f"Provider {provider_type} is not yet implemented.")

provider_manager = ProviderManager()
