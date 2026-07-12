"""
Analysis Response Schemas
=========================

Pydantic models that define the API contract for the analysis engine output.

Design principles:
- One model per analysis category — mirrors the separation of responsibilities
  inside AnalysisService.
- All models are composed into a single root AnalysisResponse so the API
  returns one clean, structured object.
- These models sit at the API boundary only. The internal domain objects
  (dataclasses inside analysis_service.py) are converted to these models
  before reaching the endpoint.

Why Pydantic here and dataclasses internally:
- Pydantic adds validation, JSON serialisation, and OpenAPI schema generation.
  That's exactly what you want at the HTTP boundary.
- For the internal domain objects that travel between services, plain frozen
  dataclasses are lighter and carry no serialisation overhead.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# 1. Page Metadata
# ---------------------------------------------------------------------------

class MetadataSchema(BaseModel):
    """
    Core page identity and SEO metadata.

    These fields are the first thing a QA engineer or AI model would check
    when assessing a page — they define what the page claims to be.
    """
    title: str
    description: Optional[str]
    canonical_url: Optional[str]
    language: Optional[str]
    charset: Optional[str]
    current_url: str


# ---------------------------------------------------------------------------
# 2. Heading Analysis
# ---------------------------------------------------------------------------

class HeadingSchema(BaseModel):
    """
    Document heading structure.

    Heading hierarchy is one of the most common accessibility and SEO issues.
    Returning the actual text (not just counts) lets an AI model check for
    keyword consistency, missing H1, or illogical structure.
    """
    h1: list[str]
    h2: list[str]
    h3: list[str]
    h1_count: int
    h2_count: int
    h3_count: int


# ---------------------------------------------------------------------------
# 3. Image Analysis
# ---------------------------------------------------------------------------

class ImageSchema(BaseModel):
    """
    Image accessibility and loading characteristics.

    missing_alt: images with no alt attribute at all (WCAG 2.1 failure)
    empty_alt:   images with alt="" (intentional — decorative images)
    broken:      images the browser loaded but decoded as empty (naturalWidth=0)
    lazy_loaded: images with loading="lazy" (affects LCP and screenshot timing)
    """
    total: int
    missing_alt: int
    empty_alt: int
    broken: int
    lazy_loaded: int


# ---------------------------------------------------------------------------
# 4. Link Analysis
# ---------------------------------------------------------------------------

class LinkSchema(BaseModel):
    """
    Link inventory for navigation and SEO auditing.

    internal vs external is determined by hostname comparison against the
    page's own origin — a fast, purely client-side heuristic.
    duplicate_count counts links whose normalised href appears more than once.
    """
    total: int
    internal: int
    external: int
    no_href: int
    duplicate_count: int


# ---------------------------------------------------------------------------
# 5. Form Analysis
# ---------------------------------------------------------------------------

class FormSchema(BaseModel):
    """
    Form field inventory.

    Returns counts per input type so an AI model can detect common issues:
    - Missing email validation fields
    - Password fields without confirmation
    - Required fields ratio (required / total inputs)
    """
    total: int
    inputs: int
    text: int
    email: int
    password: int
    checkbox: int
    radio: int
    textarea: int
    select: int
    buttons: int
    required: int


# ---------------------------------------------------------------------------
# 6. Asset Analysis
# ---------------------------------------------------------------------------

class AssetSchema(BaseModel):
    """
    Page resource inventory.

    Returns element counts only — no URLs, no file sizes.
    This milestone is about data collection; content auditing is a future step.
    """
    scripts: int
    stylesheets: int
    fonts: int
    videos: int
    iframes: int
    svgs: int
    canvases: int


# ---------------------------------------------------------------------------
# 7. Browser Storage
# ---------------------------------------------------------------------------

class StorageSchema(BaseModel):
    """
    Browser storage key counts.

    Returns counts only — never keys or values.
    Cookie/storage VALUES may contain PII or authentication tokens and must
    never be included in analysis output.
    """
    cookies: int
    local_storage: int
    session_storage: int


# ---------------------------------------------------------------------------
# 8. DOM Statistics
# ---------------------------------------------------------------------------

class DomSchema(BaseModel):
    """
    Structural DOM metrics.

    These are proxy measurements for page complexity. An AI model can use
    them to flag pages that are unusually large, deeply nested, or sparse.
    height/width are in pixels (document scroll dimensions, not viewport).
    """
    total_nodes: int
    height: int
    width: int
    buttons: int
    tables: int
    lists: int
    paragraphs: int


# ---------------------------------------------------------------------------
# 9. Console Messages
# ---------------------------------------------------------------------------

class ConsoleMessageSchema(BaseModel):
    """
    A single console event captured during page load.

    timestamp is a float (Unix epoch seconds) when available, else None.
    """
    type: str
    text: str
    timestamp: Optional[float]


class ConsoleSchema(BaseModel):
    """
    Console events grouped by severity.

    Only errors and warnings are captured by default — log/debug messages
    are too noisy for most analysis workflows and are discarded at the
    EventCollector level.
    """
    errors: list[ConsoleMessageSchema]
    warnings: list[ConsoleMessageSchema]


# ---------------------------------------------------------------------------
# 10. Failed Network Requests
# ---------------------------------------------------------------------------

class NetworkFailureSchema(BaseModel):
    """
    A single failed network request captured during page load.

    status is always None for truly failed requests — a failure means
    no HTTP response was received (DNS failure, connection refused, timeout).
    HTTP 4xx/5xx responses are NOT failures at the Playwright network level;
    they are successful requests that carry an error status code.

    failure_reason is the Playwright/Chromium net error string,
    e.g. "net::ERR_NAME_NOT_RESOLVED".
    """
    url: str
    method: str
    failure_reason: Optional[str]
    timestamp: Optional[float]


class NetworkSchema(BaseModel):
    """All network failures captured during page load."""
    failed_requests: list[NetworkFailureSchema]


# ---------------------------------------------------------------------------
# Root Analysis Response
# ---------------------------------------------------------------------------

class AnalysisResponse(BaseModel):
    """
    Composite analysis result — the root object returned in the scan response.

    Each field is an independently validated, strongly-typed sub-model.
    This design means:
    - AI consumers can subscribe to only the categories they need.
    - Individual categories can be extended (or replaced) without changing
      the others.
    - The OpenAPI schema in /docs gives a fully expanded, self-documenting
      view of every field.
    """
    metadata: MetadataSchema
    headings: HeadingSchema
    images: ImageSchema
    links: LinkSchema
    forms: FormSchema
    assets: AssetSchema
    storage: StorageSchema
    dom: DomSchema
    console: ConsoleSchema
    network: NetworkSchema
