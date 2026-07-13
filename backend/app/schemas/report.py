"""
Report Schemas
==============

Pydantic models for the master scan report and scan list API responses.

The master report (ScanReportSchema) is the canonical representation of
a completed scan. It is:
    - Persisted as report.json in the artifact directory
    - Returned by GET /api/v1/scans/{scan_id}
    - The single source of truth for everything produced during a scan

Design decisions:
    - Reuses existing AnalysisResponse and ReadinessReportSchema rather
      than duplicating their fields. This avoids data drift and ensures
      the report contains exactly what the API returns.
    - ScanInfoSchema captures scan lifecycle metadata (timing, status)
      separately from the analysis results.
    - VersionInfoSchema locks down the tool versions used for each scan.
      This is critical for compatibility when comparing reports generated
      months apart.
    - report_schema_version starts at "1.0.0". Bump this when the report
      structure changes — consumers can use it to handle format migrations.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.schemas.analysis import AnalysisResponse
from app.schemas.scan import ReadinessReportSchema


# ---------------------------------------------------------------------------
# Scan Information
# ---------------------------------------------------------------------------

class ScanInfoSchema(BaseModel):
    """
    Metadata about the scan execution itself (not the page content).

    This is the "who, when, how" of the scan — distinct from the "what"
    captured by AnalysisResponse.
    """
    scan_id: str
    url: str
    started_at: str
    completed_at: str
    duration_seconds: float
    browser_mode: str
    status: str


# ---------------------------------------------------------------------------
# Version Information
# ---------------------------------------------------------------------------

class VersionInfoSchema(BaseModel):
    """
    Software versions used to produce this report.

    Locking versions into each report ensures reproducibility.
    If a report from January looks different from one in July,
    these fields tell you whether the tool changed underneath.

    Attributes:
        qaforge_version:       Application version (from FastAPI app.version).
        report_schema_version: Report format version. Bump on structural changes.
        playwright_version:    Playwright library version.
        browser_version:       Chromium version used for this specific scan.
    """
    qaforge_version: str
    report_schema_version: str = "1.0.0"
    playwright_version: str
    browser_version: str


# ---------------------------------------------------------------------------
# Master Report
# ---------------------------------------------------------------------------

class ScanReportSchema(BaseModel):
    """
    The complete master report for a scan.

    This model is the canonical scan artifact. It composes:
    - scan_info: execution metadata (timing, status, mode)
    - analysis: full page analysis (10 categories)
    - readiness: page readiness check results
    - versions: tool version information
    - warnings: readiness warnings (e.g., "images timed out")
    - scan_quality_score: 0.0–1.0 confidence in visual fidelity
    """
    scan_info: ScanInfoSchema
    analysis: AnalysisResponse
    readiness: Optional[ReadinessReportSchema] = None
    versions: VersionInfoSchema
    warnings: list[str] = []
    scan_quality_score: float = 1.0


# ---------------------------------------------------------------------------
# Scan List Item
# ---------------------------------------------------------------------------

class ScanListItemSchema(BaseModel):
    """
    Lightweight scan summary for the list endpoint.

    GET /api/v1/scans returns an array of these. They contain just enough
    information for a scan history UI — the full report is available via
    GET /api/v1/scans/{scan_id}.
    """
    scan_id: str
    url: str
    status: str
    created_at: Optional[str] = None
    duration_seconds: Optional[float] = None
