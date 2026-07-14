import time
import logging
from typing import Callable, Any, TypeVar

T = TypeVar('T')

logger = logging.getLogger(__name__)

class RetryHandler:
    """
    Standardized exponential backoff retry logic for AI API calls.
    Handles rate limits, temporary timeouts, and malformed responses.
    """

    @staticmethod
    def execute_with_retry(
        func: Callable[[], T],
        max_retries: int = 3,
        base_delay_sec: float = 2.0
    ) -> T:
        """
        Executes a function, retrying on Exception with exponential backoff.
        """
        attempt = 0
        while attempt < max_retries:
            try:
                return func()
            except Exception as e:
                attempt += 1
                if attempt >= max_retries:
                    logger.error(f"AI request failed after {max_retries} attempts. Final error: {e}")
                    raise e
                
                # Exponential backoff: 2s, 4s, 8s...
                sleep_time = base_delay_sec * (2 ** (attempt - 1))
                logger.warning(f"AI request failed (attempt {attempt}/{max_retries}). Retrying in {sleep_time}s. Error: {e}")
                time.sleep(sleep_time)

retry_handler = RetryHandler()
