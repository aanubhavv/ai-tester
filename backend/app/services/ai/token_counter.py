import json
from typing import Any

class TokenCounter:
    """
    Utility for estimating tokens before sending a request.
    Useful for proactive chunking or warning before hitting context limits.
    """

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        A rough estimation method (approx 4 chars per token for English).
        In a production system, use tiktoken (for OpenAI) or the provider's specific tokenizer.
        """
        if not text:
            return 0
        return len(text) // 4

    @staticmethod
    def estimate_dict_tokens(data: dict) -> int:
        """Estimates tokens for a dictionary (e.g. JSON payloads)."""
        text = json.dumps(data)
        return TokenCounter.estimate_tokens(text)

token_counter = TokenCounter()
