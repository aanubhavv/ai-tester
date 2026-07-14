from typing import Any
from fastapi import APIRouter

from app.schemas.ai import AIProviderType
from app.services.ai.provider_manager import provider_manager
from app.config.ai import ai_config

router = APIRouter()

@router.get("/health")
def ai_health_check() -> Any:
    """
    Checks if the default configured AI provider is reachable.
    """
    provider = provider_manager.get_provider(ai_config.DEFAULT_PROVIDER)
    is_healthy = provider.health_check()
    
    if is_healthy:
        return {"status": "healthy", "provider": ai_config.DEFAULT_PROVIDER}
    return {"status": "unhealthy", "provider": ai_config.DEFAULT_PROVIDER}

@router.get("/providers")
def get_providers() -> Any:
    """
    Returns available AI providers.
    """
    return {
        "active_providers": [p.value for p in AIProviderType],
        "default": ai_config.DEFAULT_PROVIDER
    }
