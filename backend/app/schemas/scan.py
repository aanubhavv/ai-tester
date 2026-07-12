from typing import Optional

from pydantic import BaseModel, HttpUrl
from app.schemas.analysis import AnalysisResponse


class ScanRequest(BaseModel):
    """
    Request model for the scan endpoint.

    Uses Pydantic's HttpUrl type to validate that the incoming URL
    is well-formed (has a scheme like https://, a valid host, etc.)
    before any browser logic runs. If the URL is malformed, FastAPI
    automatically returns a 422 with a clear validation error —
    we never even touch Playwright.
    """

    url: HttpUrl


# ---------------------------------------------------------------------------
# Readiness Report Models
# ---------------------------------------------------------------------------
# These models represent the readiness engine's structured output in the
# API response. They convert from the internal ReadinessResult/CheckResult
# dataclasses (in readiness_models.py) to Pydantic models for JSON
# serialisation and OpenAPI documentation.

class ReadinessCheckSchema(BaseModel):
    """
    A single readiness check result as returned in the API response.

    Maps 1:1 to the internal CheckResult dataclass, but using Pydantic
    for serialisation and schema generation.
    """
    name: str
    passed: bool
    elapsed_ms: float
    message: str


class ReadinessReportSchema(BaseModel):
    """
    Aggregated readiness report for the scan response.

    Splits checks into completed (passed) and failed (timed out / errored)
    for easy consumption by API clients and future AI analysis.
    """
    completed: list[ReadinessCheckSchema]
    failed: list[ReadinessCheckSchema]
    total_elapsed_seconds: float
    scan_quality_score: float


# ---------------------------------------------------------------------------
# Scan Response
# ---------------------------------------------------------------------------

class ScanResponse(BaseModel):
    """
    Response model for a successful scan.

    Every field maps directly to the API contract. Using a Pydantic model
    (instead of returning a raw dict) gives us automatic serialization,
    type safety, and self-documenting Swagger schemas.

    New fields (warnings, scan_quality_score, readiness) have defaults so
    existing API consumers are not broken by this change.
    """

    success: bool
    title: str
    final_url: str
    status: int
    load_time: float
    screenshot: str
    analysis: AnalysisResponse

    # --- New fields from readiness engine refactor ---
    # These provide visibility into scan quality and which readiness
    # checks passed or timed out. Empty/default values maintain backward
    # compatibility with existing clients.
    warnings: list[str] = []
    scan_quality_score: float = 1.0
    readiness: Optional[ReadinessReportSchema] = None
