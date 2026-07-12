from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel
from app.schemas.analysis import AnalysisResponse


# ---------------------------------------------------------------------------
# Scan Options (internal transport object)
# ---------------------------------------------------------------------------
# This is NOT a Pydantic model because it never touches JSON serialization.
# It's an internal dataclass that the endpoint constructs from query params
# and passes to BrowserService. Using a dataclass keeps it lightweight and
# makes it clear this is not an API boundary type.
#
# Future-proof: when you need to add viewport, locale, proxy, user-agent,
# cookies, etc., add them as fields here. BrowserService.scan_url() accepts
# a single ScanOptions object, so its signature never changes.

@dataclass(frozen=True)
class ScanOptions:
    """
    Per-request scan configuration passed from the endpoint to BrowserService.

    Every scan option that can vary between requests lives here.
    Environment-level defaults (readiness timeouts, scroll settings) stay in
    config.py / ReadinessConfig — they don't change per request.

    Attributes:
        url:      The target URL to scan. Already validated by the endpoint.
        headless: Whether to run the browser in headless mode.
                  True (default) = invisible headless browser.
                  False = visible headed browser window.
    """
    url: str
    headless: bool = True

    @property
    def browser_mode(self) -> str:
        """Human-readable label for the API response."""
        return "headless" if self.headless else "headed"


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

    New fields (warnings, scan_quality_score, readiness, browser_mode)
    have defaults so existing API consumers are not broken by this change.
    """

    success: bool
    browser_mode: str = "headless"
    title: str
    final_url: str
    status: int
    load_time: float
    screenshot: str
    analysis: AnalysisResponse

    # --- Fields from readiness engine refactor ---
    warnings: list[str] = []
    scan_quality_score: float = 1.0
    readiness: Optional[ReadinessReportSchema] = None

