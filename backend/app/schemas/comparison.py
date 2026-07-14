from typing import Optional
from pydantic import BaseModel, Field

class ComparisonRequest(BaseModel):
    """
    Request payload for creating a new visual comparison.
    """
    project_id: str = Field(..., description="The ID of the project.")
    baseline_scan_id: str = Field(..., description="The ID of the baseline scan artifact.")
    current_scan_id: str = Field(..., description="The ID of the current scan artifact to compare against.")
    threshold: Optional[float] = Field(
        0.05, 
        description="Threshold (0.0 to 1.0) for ignoring small pixel differences. Default 0.05."
    )
    ignored_selectors: Optional[list[str]] = Field(
        default_factory=list,
        description="List of CSS selectors to mask out before comparison (e.g. '.cookie-banner')."
    )

class ChangedRegion(BaseModel):
    """
    Represents a rectangular region on the screen where visual differences were detected.
    Future AI modules will use these coordinates to inspect exactly what changed.
    """
    x: int
    y: int
    width: int
    height: int
    area: int

class DiffStatistics(BaseModel):
    """
    Quantitative metrics about the visual difference between the baseline and current screenshots.
    """
    difference_percentage: float
    changed_pixels: int
    image_width: int
    image_height: int

class ComparisonResponse(BaseModel):
    """
    Response payload returned by the POST /api/v1/compare endpoint.
    """
    comparison_id: str
    baseline_scan_id: str
    current_scan_id: str
    passed: bool
    statistics: DiffStatistics
    changed_regions: list[ChangedRegion]
    warnings: list[str] = []
    diff_image_url: str
