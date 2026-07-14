import hashlib
import json
from typing import Optional, Any
from pydantic import BaseModel

class AICache:
    """
    A simple memory cache to prevent duplicate AI calls during development.
    In production, this would be backed by Redis.
    """
    
    def __init__(self):
        self._cache = {}

    def _generate_key(self, task: str, prompt: str, model: str) -> str:
        """Generates a deterministic hash for the request."""
        # We hash the prompt to keep keys short, while grouping by task and model
        prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
        return f"{task}:{model}:{prompt_hash}"

    def get(self, task: str, prompt: str, model: str) -> Optional[Any]:
        key = self._generate_key(task, prompt, model)
        return self._cache.get(key)

    def set(self, task: str, prompt: str, model: str, data: Any):
        key = self._generate_key(task, prompt, model)
        # We just store the data in memory.
        self._cache[key] = data
        
    def clear(self):
        self._cache.clear()

ai_cache = AICache()
