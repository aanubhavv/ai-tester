from pydantic import BaseModel, HttpUrl


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


class ScanResponse(BaseModel):
    """
    Response model for a successful scan.

    Every field maps directly to the API contract defined in the
    milestone spec. Using a Pydantic model (instead of returning
    a raw dict) gives us automatic serialization, type safety,
    and self-documenting Swagger schemas.
    """

    success: bool
    title: str
    final_url: str
    status: int
    load_time: float
    screenshot: str
