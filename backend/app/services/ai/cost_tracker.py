import logging
from app.schemas.ai import AIUsageMetrics

logger = logging.getLogger(__name__)

class CostTracker:
    """
    Central utility for tracking and logging AI costs across the platform.
    In a real system, this would write to a PostgreSQL table for billing and analytics.
    """

    @staticmethod
    def record_usage(task: str, metrics: AIUsageMetrics):
        """
        Logs the cost and token usage of an AI request.
        """
        # In the future: db.session.add(UsageRecord(...))
        logger.info(
            f"[AI_COST] Task: {task} | Provider: {metrics.provider.value} | "
            f"Model: {metrics.model} | Tokens: {metrics.total_tokens} | "
            f"Cost: ${metrics.estimated_cost_usd:.6f} | Duration: {metrics.duration_ms}ms"
        )
        
        # For terminal visibility during development
        print(f"💰 AI Task '{task}' via {metrics.provider.value}/{metrics.model} consumed {metrics.total_tokens} tokens (${metrics.estimated_cost_usd:.6f}) in {metrics.duration_ms}ms")

cost_tracker = CostTracker()
