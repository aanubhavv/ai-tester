from pydantic import BaseModel
from typing import Optional
from app.schemas.comparison import DiffStatistics, ChangedRegion

class ComparisonInfoSchema(BaseModel):
    """
    Metadata about the comparison execution.
    """
    comparison_id: str
    baseline_scan_id: str
    current_scan_id: str
    compared_at: str
    duration_seconds: float
    threshold_used: float
    ignored_selectors: list[str]

class RegressionReportSchema(BaseModel):
    """
    The master artifact representation for a visual regression comparison.
    Persisted to 'report.json' within the comparison artifact directory.
    """
    info: ComparisonInfoSchema
    status: str  # "passed", "failed", "error"
    statistics: Optional[DiffStatistics] = None
    changed_regions: list[ChangedRegion] = []
    warnings: list[str] = []
    error_message: Optional[str] = None
