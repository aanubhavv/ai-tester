import logging
import time

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout, Error as PlaywrightError

# Grab version at module level — inside scan_url(), the `playwright` name
# is shadowed by `with sync_playwright() as playwright:`.
import importlib.metadata
_PLAYWRIGHT_VERSION = importlib.metadata.version("playwright")

from app.schemas.scan import ScanOptions
from app.services.page_readiness import PageReadinessEngine, ReadinessConfig
from app.services.readiness_models import ReadinessResult
from app.services.analysis_service import AnalysisService, EventCollector, to_analysis_response
from app.core.config import settings

logger = logging.getLogger(__name__)


class ScanError(Exception):
    """
    Custom domain exception for scan failures.

    This is the ONLY exception the scan endpoint needs to catch.
    All Playwright-level errors (timeouts, DNS failures, SSL issues,
    connection refused, etc.) are caught inside BrowserService and
    re-raised as ScanError with a user-friendly message.

    This keeps the endpoint code minimal — it doesn't need to know
    about Playwright's exception hierarchy at all.
    """

    pass


def _readiness_to_dict(result: ReadinessResult) -> dict:
    """
    Convert a ReadinessResult into a plain dict for the scan response.

    This is a module-level helper (not a method on ReadinessResult) because
    serialisation format is an API concern, not a domain concern. The
    ReadinessResult dataclass stays independent of how it's presented.
    """
    def check_to_dict(check) -> dict:
        return {
            "name": check.name.value,
            "passed": check.passed,
            "elapsed_ms": check.elapsed_ms,
            "message": check.message,
        }

    return {
        "completed": [check_to_dict(c) for c in result.completed_checks],
        "failed": [check_to_dict(c) for c in result.failed_checks],
        "total_elapsed_seconds": result.total_elapsed_seconds,
        "scan_quality_score": result.scan_quality_score,
    }


class BrowserService:
    """
    Encapsulates all Playwright browser automation logic.

    This service is the core of the scanner feature. It owns the entire
    lifecycle: launching the browser, navigating to the URL, collecting
    page data, taking a screenshot, and closing the browser.

    The endpoint never touches Playwright directly — it calls
    BrowserService.scan_url() and gets back a plain dictionary.

    Design notes:
    - Uses Playwright's SYNC API (not async) for simplicity in this
      first milestone. FastAPI runs sync endpoints in a threadpool,
      so the server stays responsive.
    - The browser is launched and closed within each scan_url() call.
      This is intentional — no long-lived browser processes to manage,
      no state leaking between requests. We can optimize later if
      performance becomes a concern.
    - As of Milestone 5, screenshot persistence is handled by
      ArtifactService. BrowserService returns raw screenshot bytes
      instead of saving to disk.
    """

    def scan_url(
        self,
        options: ScanOptions,
        readiness_config: ReadinessConfig | None = None,
    ) -> dict:
        """
        Open a browser, navigate to the URL, and collect page information.

        This is the single public method of the service. It:
        1. Launches a Chromium browser (headless or headed per options)
        2. Navigates to the given URL (using the configured wait strategy)
        3. Runs the Page Readiness Engine to wait for the page to stabilize
        4. Inspects the ReadinessResult — continues on non-critical failures,
           aborts only on critical failures
        5. Extracts the page title and final URL (after redirects)
        6. Captures a full-page screenshot
        7. Returns all collected data as a dictionary, including readiness
           warnings and quality score

        Args:
            options: Per-request scan configuration (URL, headless, and
                     future options like viewport, locale, proxy).
            readiness_config: Optional readiness configuration. If None,
                              uses default ReadinessConfig values.

        Raises:
            ScanError: If any browser or network error occurs, or if the
                       readiness engine reports a critical failure.
                       The original error is logged, and a clean
                       user-facing message is raised.
        """
        config = readiness_config or ReadinessConfig()
        url = options.url
        logger.info(f"Starting scan for URL: {url} (mode={options.browser_mode})")
        start_time = time.time()

        try:
            with sync_playwright() as playwright:
                if settings.browserless_ws_endpoint:
                    logger.info(f"Scan connecting to Browserless at {settings.browserless_ws_endpoint}")
                    browser = playwright.chromium.connect_over_cdp(settings.browserless_ws_endpoint)
                else:
                    logger.info(f"Scan launching local Playwright browser (headless={options.headless})")
                    browser = playwright.chromium.launch(
                        headless=options.headless,
                        args=['--no-sandbox', '--disable-dev-shm-usage']
                    )

                try:
                    page = browser.new_page()

                    # EventCollector MUST be created before goto().
                    # It registers page.on("console") and page.on("requestfailed")
                    # hooks immediately. Any events that fire before these hooks
                    # are registered are lost permanently — there is no replay.
                    event_collector = EventCollector(page)

                    # Navigate to the URL.
                    # The wait_until strategy is configurable:
                    # - 'domcontentloaded' (new default): just wait for HTML to
                    #   be parsed. Fast and reliable — the readiness engine
                    #   handles all deeper checks.
                    # - 'networkidle': wait for 0 network connections for 500ms.
                    #   Can timeout on SPAs with continuous polling/WebSockets.
                    wait_strategy = config.navigation_wait_strategy
                    response = page.goto(url, wait_until=wait_strategy, timeout=30000)

                    # Run the Page Readiness Engine.
                    # This is where the real waiting happens — fonts, images,
                    # skeleton detection, DOM stability, layout stability,
                    # and scroll discovery.
                    #
                    # The engine returns a structured ReadinessResult instead
                    # of None. BrowserService inspects it to decide whether
                    # to continue or abort.
                    readiness_engine = PageReadinessEngine(page, config)
                    readiness_result = readiness_engine.wait_until_ready()

                    # Critical failure gate.
                    # If the readiness engine reports a critical failure (e.g.,
                    # page crashed during checks), abort the scan. In practice,
                    # critical failures (DNS, navigation) are caught by the
                    # try/except around goto(), so this is a safety net.
                    if readiness_result.has_critical_failure:
                        failed_names = ", ".join(
                            c.name.value for c in readiness_result.failed_checks
                            if c.criticality.value == "critical"
                        )
                        raise ScanError(
                            f"Critical readiness check(s) failed for '{url}': "
                            f"{failed_names}. Scan aborted."
                        )

                    # Calculate load time AFTER readiness completes.
                    # From the user's perspective, the page isn't "loaded"
                    # until it's visually stable.
                    load_time = round(time.time() - start_time, 2)

                    # Extract page information
                    title = self._get_page_title(page)
                    final_url = page.url
                    status_code = self._get_status_code(response)

                    # Capture screenshot as raw bytes.
                    # ArtifactService handles persistence — BrowserService
                    # only captures the bytes in memory.
                    screenshot_bytes = self._capture_screenshot(page)

                    # Capture browser version for the report.
                    browser_version = self._get_browser_version(browser)

                    # Run the Analysis Engine.
                    # Receives the stabilised page and the event_collector
                    # that has been accumulating console/network events since
                    # before goto(). Returns a strongly-typed AnalysisResult.
                    analysis_result = AnalysisService(page, event_collector).run()
                    # Convert the internal dataclass to the Pydantic response
                    # model so ScanResponse(**result) works at the endpoint.
                    analysis_response = to_analysis_response(analysis_result)

                    logger.info(
                        f"Scan completed for {url} — "
                        f"title='{title}', status={status_code}, "
                        f"load_time={load_time}s, "
                        f"quality={readiness_result.scan_quality_score:.1%}"
                    )

                    return {
                        "success": True,
                        "browser_mode": options.browser_mode,
                        "title": title,
                        "final_url": final_url,
                        "status": status_code,
                        "load_time": load_time,
                        "screenshot_bytes": screenshot_bytes,
                        "analysis": analysis_response,
                        "warnings": list(readiness_result.warnings),
                        "scan_quality_score": readiness_result.scan_quality_score,
                        "readiness": _readiness_to_dict(readiness_result),
                        "browser_version": browser_version,
                        "playwright_version": _PLAYWRIGHT_VERSION,
                    }
                finally:
                    # Always close the browser, even if an error occurs.
                    # This prevents zombie Chromium processes.
                    browser.close()

        except PlaywrightTimeout:
            logger.error(f"Timeout while scanning {url}")
            raise ScanError(
                f"The page at '{url}' took too long to load. "
                f"It may be slow or unresponsive."
            )

        except PlaywrightError as exc:
            error_message = str(exc).lower()
            logger.error(f"Playwright error scanning {url}: {exc}")

            # Map common Playwright errors to user-friendly messages.
            # Playwright wraps network-level failures in its own Error
            # class, so we inspect the message to classify them.
            if "net::err_name_not_resolved" in error_message:
                raise ScanError(
                    f"Could not resolve the domain for '{url}'. "
                    f"Please check that the URL is correct."
                )
            elif "net::err_connection_refused" in error_message:
                raise ScanError(
                    f"Connection refused by '{url}'. "
                    f"The server may be down or not accepting connections."
                )
            elif "net::err_cert" in error_message or "ssl" in error_message:
                raise ScanError(
                    f"SSL/certificate error for '{url}'. "
                    f"The site may have an invalid or expired certificate."
                )
            elif "net::err_connection_timed_out" in error_message:
                raise ScanError(
                    f"Connection timed out for '{url}'. "
                    f"The server did not respond in time."
                )
            else:
                raise ScanError(
                    f"Failed to scan '{url}': {exc}"
                )

        except ScanError:
            # Re-raise ScanErrors without wrapping them again
            raise

        except Exception as exc:
            # Catch-all for truly unexpected errors (e.g., OS-level issues).
            # We still wrap them in ScanError so the endpoint has a
            # single exception type to handle.
            logger.error(f"Unexpected error scanning {url}: {exc}", exc_info=True)
            raise ScanError(
                f"An unexpected error occurred while scanning '{url}'. "
                f"Please try again later."
            )

    def _get_page_title(self, page) -> str:
        """
        Extract the page title, returning a fallback if empty.

        Some pages have no <title> tag — we handle that gracefully
        instead of returning an empty string.
        """
        title = page.title()
        return title if title else "No title found"

    def _get_status_code(self, response) -> int:
        """
        Extract the HTTP status code from the navigation response.

        The response can be None in rare cases (e.g., if the page
        navigated via JavaScript before the initial response completed).
        We return 0 as a sentinel value rather than crashing.
        """
        if response is None:
            return 0
        return response.status

    def _capture_screenshot(self, page) -> bytes:
        """
        Capture a full-page screenshot and return raw PNG bytes.

        Returns bytes instead of saving to disk. The caller (scan endpoint)
        passes these bytes to ArtifactService for persistence. This keeps
        BrowserService free of filesystem concerns.
        """
        screenshot_bytes = page.screenshot(full_page=True)
        logger.info(f"Screenshot captured ({len(screenshot_bytes)} bytes)")
        return screenshot_bytes

    def _get_browser_version(self, browser) -> str:
        """
        Extract the browser version string.

        Used by the report's VersionInfoSchema to record which Chromium
        build produced this scan. Returns a fallback if unavailable.
        """
        try:
            return browser.version
        except Exception:
            return "unknown"
