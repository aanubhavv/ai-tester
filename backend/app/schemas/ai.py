from enum import Enum
from typing import Optional, Dict, Any, Type
from pydantic import BaseModel, Field

class AIProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"

class TaskConfiguration(BaseModel):
    """Configuration mapping a specific task to a provider and model."""
    provider: AIProviderType
    model: str
    temperature: float = 0.2
    max_tokens: int = 4096
    retries: int = 3
    timeout: int = 60

class AIUsageMetrics(BaseModel):
    """Tracks token usage and estimated cost for a single request."""
    provider: AIProviderType
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    duration_ms: int = 0

class AIResponseContext(BaseModel):
    """Wrapper for returning both the structured data and the usage metrics."""
    data: Any = Field(description="The parsed structured data or raw text returned by the model")
    metrics: AIUsageMetrics

class AIRequestOptions(BaseModel):
    """Overrides for a specific AI request."""
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    retries: Optional[int] = None
    timeout: Optional[int] = None
    
    # We pass the class type directly for structured outputs, not instantiated
    # but Pydantic BaseModel handles Type[BaseModel] well in pure python logic
