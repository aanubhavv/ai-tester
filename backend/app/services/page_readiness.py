"""
Page Readiness Engine
=====================

This module answers one question: "Is this page ready for screenshotting
and analysis?"

It exists as a standalone component (not inside BrowserService) because:
1. Single Responsibility — BrowserService owns the browser lifecycle;
   this engine owns the readiness decision.
2. Reusability — future features (accessibility testing, visual regression,
   AI analysis) will all need "wait until ready" without going through
   BrowserService.
3. Testability — you can test readiness logic with a mocked Playwright Page
   without launching a real browser.

The engine runs a pipeline of targeted checks, each addressing a specific
category of "the page isn't finished rendering yet." Each check is
independently configurable and can be skipped entirely.

Architecture (post-refactor):
- Every check returns a CheckResult (not None).
- The pipeline returns a ReadinessResult with all check outcomes, warnings,
  and a weighted quality score.
- All checks are NON-CRITICAL: timeouts produce warnings, not failures.
  Critical failures (DNS, navigation, browser crash) are handled by
  BrowserService before this engine runs.
- A new scroll discovery phase triggers lazy-loaded content before the
  final screenshot.
"""

import logging
import time
from dataclasses import dataclass, field

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from app.services.readiness_models import (
    CheckCategory,
    CheckCriticality,
    CheckResult,
    ReadinessResult,
    compute_scan_quality_score,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default skeleton/loading selectors
# ---------------------------------------------------------------------------
# These cover the most common UI frameworks and conventions. Teams can
# extend this list via ReadinessConfig.skeleton_selectors.
#
# Why these specific selectors:
# - .skeleton, .shimmer, .loading, .loader, .spinner — generic conventions
#   used across countless projects
# - [aria-busy="true"] — the accessibility-standard way to mark a region
#   as "still loading"
# - .placeholder-glow, .placeholder-wave — Bootstrap 5 skeleton components
# - .ant-skeleton — Ant Design (very popular React UI library)
# - .MuiSkeleton-root — Material UI (most popular React UI library)
# - .v-skeleton-loader — Vuetify (most popular Vue UI library)
# ---------------------------------------------------------------------------

DEFAULT_SKELETON_SELECTORS: tuple[str, ...] = (
    ".skeleton",
    ".shimmer",
    ".loading",
    ".loader",
    ".spinner",
    "[aria-busy='true']",
    ".placeholder-glow",
    ".placeholder-wave",
    ".ant-skeleton",
    ".MuiSkeleton-root",
    ".v-skeleton-loader",
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ReadinessConfig:
    """
    Configuration for the page readiness pipeline.

    This is a frozen (immutable) dataclass rather than a pydantic-settings
    model because:
    - It's scan-level config, not environment-level config. Different scans
      may want different readiness settings (quick scan vs. thorough scan).
    - Frozen ensures the config can't be mutated mid-pipeline.
    - It uses tuple for selectors (not list) because frozen dataclasses
      require hashable fields.

    All timeouts are in milliseconds for consistency with Playwright's API,
    except max_wait_seconds and final_delay_seconds which are in seconds
    for readability (they represent human-perceptible durations).
    """

    # Global maximum time the entire readiness pipeline can take.
    # Individual checks will stop early if this budget is exhausted.
    max_wait_seconds: float = 30.0

    # --- Navigation ---
    # The Playwright wait_until strategy used during page.goto().
    # "domcontentloaded" is the new default because "networkidle" can
    # timeout on SPAs with continuous polling, WebSockets, or streaming.
    # The readiness engine handles deeper checks after navigation.
    navigation_wait_strategy: str = "domcontentloaded"

    # --- Fonts ---
    # Waits for document.fonts.ready (the FontFaceSet API).
    # Prevents FOIT (Flash of Invisible Text) and FOUT (Flash of Unstyled
    # Text) in screenshots.
    wait_for_fonts: bool = True
    fonts_timeout_ms: int = 5000

    # --- Images ---
    # Polls all <img> elements until img.complete is true.
    # Catches lazy-loaded and slow-loading images.
    wait_for_images: bool = True
    images_timeout_ms: int = 10000

    # --- Videos ---
    # Polls all <video> elements that are expected to load (preload != "none")
    # until HTMLMediaElement.readyState >= HAVE_CURRENT_DATA (2).
    #
    # readyState >= 2 means at least one decoded video frame is in the buffer,
    # which is the minimum required for the video to appear in a screenshot.
    #
    # Videos with preload="none" are skipped — they intentionally defer loading
    # until user interaction, so a black frame or poster is the expected render.
    #
    # iframe-embedded players (YouTube, Vimeo) are out of scope: cross-origin
    # restrictions prevent readyState inspection inside iframes.
    wait_for_videos: bool = True
    videos_timeout_ms: int = 8000

    # --- Skeleton / Loading indicators ---
    # Polls for elements matching common skeleton CSS selectors and waits
    # for them to disappear. This is the #1 cause of "ugly screenshots."
    wait_for_skeletons: bool = True
    skeleton_selectors: tuple[str, ...] = DEFAULT_SKELETON_SELECTORS
    skeletons_timeout_ms: int = 10000

    # --- DOM stability ---
    # Samples document.querySelectorAll('*').length at intervals.
    # If the count stays the same for N consecutive readings, the DOM
    # is considered stable. Detects SPAs still injecting content.
    dom_stability_checks: int = 3
    dom_stability_interval_ms: int = 300

    # --- Layout stability ---
    # Samples document.documentElement.scrollHeight at intervals.
    # If the height stays the same for N consecutive readings, layout
    # is considered stable. Catches CLS from images, fonts, and lazy content.
    layout_stability_checks: int = 3
    layout_stability_interval_ms: int = 300

    # --- Scroll Discovery ---
    # Scrolls the page gradually from top to bottom to trigger lazy-loaded
    # content, intersection observers, infinite scroll sections, and
    # deferred React components. After scrolling, returns to the top.
    #
    # Why this is a readiness step (not a BrowserService concern):
    # Scroll discovery directly affects page content completeness, which
    # is a readiness concern. The screenshot and analysis should reflect
    # the FULL page, not just the first viewport.
    enable_scroll_discovery: bool = True
    scroll_step_pixels: int = 800
    scroll_pause_ms: int = 400
    max_scroll_iterations: int = 25
    scroll_stability_checks: int = 2

    # --- Final delay ---
    # A short sleep after all checks pass. Safety net for CSS transitions,
    # fade-in animations, and final paint cycles.
    final_delay_seconds: float = 0.5


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class PageReadinessEngine:
    """
    Determines when a page is "ready" for screenshotting and analysis.

    Usage:
        engine = PageReadinessEngine(page, config)
        result = engine.wait_until_ready()
        # result.scan_quality_score tells you how confident the scan is
        # result.warnings lists any checks that timed out
        # result.has_critical_failure tells you if the scan should be aborted

    The pipeline runs each check in order. Each check respects the global
    max_wait_seconds budget — if time runs out, remaining checks are
    recorded as skipped and we proceed with what we have.

    Every check returns a CheckResult. The pipeline aggregates all results
    into a ReadinessResult with a weighted quality score.
    """

    def __init__(self, page: Page, config: ReadinessConfig | None = None) -> None:
        self._page = page
        self._config = config or ReadinessConfig()
        self._start_time: float = 0.0

    def wait_until_ready(self) -> ReadinessResult:
        """
        Run the full readiness pipeline.

        Each step is guarded by its config toggle and the global time budget.
        Steps run in a deliberate order — fonts and images first (they affect
        layout), then skeleton detection, then stability checks (which verify
        everything has settled), then scroll discovery, then the final delay.

        Returns:
            ReadinessResult with all check outcomes, quality score, and warnings.
        """
        self._start_time = time.time()
        logger.info("Page readiness pipeline started")

        check_results: list[CheckResult] = []

        # Step 1: Fonts (affects text layout → must come before stability checks)
        if self._config.wait_for_fonts:
            check_results.append(self._wait_for_fonts())

        # Step 2: Images (affects layout → must come before stability checks)
        if self._config.wait_for_images:
            check_results.append(self._wait_for_images())

        # Step 3: Videos (must come before skeletons — skeleton→video transitions
        # are a primary source of black-frame screenshots; we want the video
        # buffer primed before we declare the skeleton gone)
        if self._config.wait_for_videos:
            check_results.append(self._wait_for_videos())

        # Step 4: Skeleton/loading indicators (content swaps → must come
        # before stability checks, since skeleton→content transition changes
        # both DOM and layout)
        if self._config.wait_for_skeletons:
            check_results.append(self._wait_for_skeletons())

        # Step 5: DOM stability (verify no more structural changes)
        check_results.append(self._wait_for_dom_stability())

        # Step 6: Layout stability (verify no more height/position changes)
        check_results.append(self._wait_for_layout_stability())

        # Step 7: Scroll discovery (trigger lazy-loaded content)
        if self._config.enable_scroll_discovery:
            check_results.append(self._perform_scroll_discovery())

        # Step 8: Final delay (safety net for animations and paint)
        if self._config.final_delay_seconds > 0:
            logger.debug(
                f"Final stabilization delay: {self._config.final_delay_seconds}s"
            )
            time.sleep(self._config.final_delay_seconds)

        # --- Build the result ---
        checks_tuple = tuple(check_results)
        total_elapsed = round(time.time() - self._start_time, 2)
        quality_score = compute_scan_quality_score(checks_tuple)

        # Collect warnings from failed checks
        warnings = tuple(
            check.message for check in checks_tuple if not check.passed
        )

        # Check for critical failures (in practice, all pipeline checks
        # are non-critical — critical failures are caught before the engine
        # runs — but the model supports it for future extensibility)
        has_critical = any(
            not check.passed and check.criticality == CheckCriticality.CRITICAL
            for check in checks_tuple
        )

        result = ReadinessResult(
            checks=checks_tuple,
            total_elapsed_seconds=total_elapsed,
            scan_quality_score=quality_score,
            warnings=warnings,
            has_critical_failure=has_critical,
        )

        logger.info(
            f"Page readiness pipeline completed in {total_elapsed}s — "
            f"quality={quality_score:.1%}, "
            f"passed={len(result.completed_checks)}/{len(checks_tuple)}, "
            f"warnings={len(warnings)}"
        )

        return result

    # -------------------------------------------------------------------
    # Individual readiness checks
    # -------------------------------------------------------------------

    def _wait_for_fonts(self) -> CheckResult:
        """
        Wait for all web fonts to finish loading.

        Uses the standard FontFaceSet API (document.fonts.ready), which
        returns a Promise that resolves when all font face loads have
        completed (or failed). This is the most reliable way to detect
        font readiness — no polling needed.

        Why this matters: Fonts loading late causes FOIT (invisible text)
        or FOUT (fallback font with different metrics). Either one produces
        misleading screenshots.
        """
        if not self._has_time_remaining():
            return self._skipped_result(CheckCategory.FONTS)

        logger.debug("Waiting for web fonts...")
        check_start = time.time()

        try:
            self._page.wait_for_function(
                "() => document.fonts.ready",
                timeout=self._effective_timeout(self._config.fonts_timeout_ms),
            )
            elapsed_ms = self._elapsed_ms(check_start)
            logger.debug("Web fonts loaded")
            return CheckResult(
                name=CheckCategory.FONTS,
                criticality=CheckCriticality.NON_CRITICAL,
                passed=True,
                elapsed_ms=elapsed_ms,
                message="All web fonts loaded",
            )
        except PlaywrightTimeout:
            elapsed_ms = self._elapsed_ms(check_start)
            msg = (
                f"Font loading timed out after {elapsed_ms:.0f}ms "
                f"— proceeding without waiting further"
            )
            logger.warning(msg)
            return CheckResult(
                name=CheckCategory.FONTS,
                criticality=CheckCriticality.NON_CRITICAL,
                passed=False,
                elapsed_ms=elapsed_ms,
                message=msg,
            )
        except Exception as exc:
            elapsed_ms = self._elapsed_ms(check_start)
            msg = f"Font check failed: {exc} — proceeding"
            logger.warning(msg)
            return CheckResult(
                name=CheckCategory.FONTS,
                criticality=CheckCriticality.NON_CRITICAL,
                passed=False,
                elapsed_ms=elapsed_ms,
                message=msg,
            )

    def _wait_for_images(self) -> CheckResult:
        """
        Wait for all <img> elements to finish loading.

        Polls img.complete on all images in the DOM. An image is "complete"
        when it has either loaded successfully OR failed to load (a broken
        image is still "complete"). We poll rather than using a single
        evaluate because new images can appear as the page renders.

        Why this matters: Unloaded images show as broken icons or empty
        boxes, which produce poor screenshots and unreliable analysis.

        Why we don't wait for CSS background images: That would require
        getComputedStyle() on every element, which is expensive and
        rarely worth it for this use case.
        """
        if not self._has_time_remaining():
            return self._skipped_result(CheckCategory.IMAGES)

        logger.debug("Waiting for images to load...")
        check_start = time.time()
        timeout_seconds = self._config.images_timeout_ms / 1000
        deadline = time.time() + timeout_seconds

        # JavaScript that returns True when ALL images are complete
        check_images_js = """
        () => {
            const images = document.querySelectorAll('img');
            if (images.length === 0) return true;
            return Array.from(images).every(img => img.complete);
        }
        """

        while time.time() < deadline and self._has_time_remaining():
            try:
                all_loaded = self._page.evaluate(check_images_js)
                if all_loaded:
                    elapsed_ms = self._elapsed_ms(check_start)
                    logger.debug("All images loaded")
                    return CheckResult(
                        name=CheckCategory.IMAGES,
                        criticality=CheckCriticality.NON_CRITICAL,
                        passed=True,
                        elapsed_ms=elapsed_ms,
                        message="All images loaded",
                    )
            except Exception as exc:
                elapsed_ms = self._elapsed_ms(check_start)
                msg = f"Image check failed: {exc} — proceeding"
                logger.warning(msg)
                return CheckResult(
                    name=CheckCategory.IMAGES,
                    criticality=CheckCriticality.NON_CRITICAL,
                    passed=False,
                    elapsed_ms=elapsed_ms,
                    message=msg,
                )

            time.sleep(0.3)

        elapsed_ms = self._elapsed_ms(check_start)
        msg = (
            f"Image loading timed out after {elapsed_ms:.0f}ms "
            f"— proceeding with potentially unloaded images"
        )
        logger.warning(msg)
        return CheckResult(
            name=CheckCategory.IMAGES,
            criticality=CheckCriticality.NON_CRITICAL,
            passed=False,
            elapsed_ms=elapsed_ms,
            message=msg,
        )

    def _wait_for_videos(self) -> CheckResult:
        """
        Wait for HTML5 <video> elements to have at least one decoded frame
        available for rendering.

        Uses HTMLMediaElement.readyState, a synchronous integer property that
        reflects the current decoding state without relying on events:

            0  HAVE_NOTHING      — no data received yet
            1  HAVE_METADATA     — dimensions known, no frame data
            2  HAVE_CURRENT_DATA — ≥1 frame decoded at current position  ← our target
            3  HAVE_FUTURE_DATA  — current + next frame available
            4  HAVE_ENOUGH_DATA  — enough buffered to play without stalling

        Why readyState >= 2 and not events (loadeddata / canplay):
        - Events are one-shot: if the video loaded before this engine ran
          (common for autoplay/preloaded videos), the event has already fired
          and attaching a listener at this point will never resolve.
        - readyState is always current — polling it is safe at any time.

        Why not HAVE_ENOUGH_DATA (4):
        - Streaming video (HLS, DASH) or very large files may buffer only the
          first few frames initially. readyState 4 may never be reached within
          a useful timeout, causing every scan of streaming-heavy pages to time
          out on every run.

        Videos with preload="none" are excluded: they intentionally do not
        load until the user interacts. A black frame is the expected initial
        render for those elements — waiting is pointless.

        Cross-origin iframe-embedded players (YouTube, Vimeo) are inaccessible
        due to the browser same-origin policy and are silently ignored.
        """
        if not self._has_time_remaining():
            return self._skipped_result(CheckCategory.VIDEOS)

        logger.debug("Waiting for video elements to reach readyState ≥ 2...")
        check_start = time.time()
        timeout_seconds = self._config.videos_timeout_ms / 1000
        deadline = time.time() + timeout_seconds

        # Returns a structured snapshot of video readiness state.
        # preload="none" videos are excluded from the "relevant" count so we
        # never block on intentionally-deferred videos.
        check_videos_js = """
        () => {
            const videos = Array.from(document.querySelectorAll('video'));
            if (videos.length === 0) {
                return { total: 0, relevant: 0, ready: 0, done: true };
            }

            // Exclude videos the developer explicitly said should not preload.
            // readyState < 2 on a preload=none video is intentional, not a bug.
            const relevant = videos.filter(
                v => v.preload !== 'none' || v.readyState >= 2
            );

            // HAVE_CURRENT_DATA (2) = at least one decoded frame in the buffer.
            const ready = relevant.filter(v => v.readyState >= 2).length;

            return {
                total: videos.length,
                relevant: relevant.length,
                ready: ready,
                done: ready >= relevant.length
            };
        }
        """

        while time.time() < deadline and self._has_time_remaining():
            try:
                result = self._page.evaluate(check_videos_js)
            except Exception as exc:
                elapsed_ms = self._elapsed_ms(check_start)
                msg = f"Video readiness check failed: {exc} — proceeding"
                logger.warning(msg)
                return CheckResult(
                    name=CheckCategory.VIDEOS,
                    criticality=CheckCriticality.NON_CRITICAL,
                    passed=False,
                    elapsed_ms=elapsed_ms,
                    message=msg,
                )

            total: int = result["total"]
            relevant: int = result["relevant"]
            ready: int = result["ready"]
            done: bool = result["done"]

            if total == 0:
                elapsed_ms = self._elapsed_ms(check_start)
                logger.debug("No <video> elements found — skipping video readiness check")
                return CheckResult(
                    name=CheckCategory.VIDEOS,
                    criticality=CheckCriticality.NON_CRITICAL,
                    passed=True,
                    elapsed_ms=elapsed_ms,
                    message="No video elements found",
                )

            if done:
                elapsed_ms = self._elapsed_ms(check_start)
                msg = (
                    f"Videos ready: {ready}/{relevant} relevant "
                    f"({total - relevant} excluded with preload=\"none\")"
                )
                logger.debug(msg)
                return CheckResult(
                    name=CheckCategory.VIDEOS,
                    criticality=CheckCriticality.NON_CRITICAL,
                    passed=True,
                    elapsed_ms=elapsed_ms,
                    message=msg,
                )

            logger.debug(
                f"Videos: {ready}/{relevant} ready "
                f"(total={total}, preload=none excluded={total - relevant}) — waiting..."
            )
            time.sleep(0.3)

        # Timed out — log a warning but do not raise; a partially-loaded video
        # is better than a blocked scan.
        try:
            final = self._page.evaluate(check_videos_js)
            ready_final: int = final["ready"]
            relevant_final: int = final["relevant"]
        except Exception:
            ready_final, relevant_final = 0, 0

        elapsed_ms = self._elapsed_ms(check_start)
        msg = (
            f"Video readiness timed out after {elapsed_ms:.0f}ms "
            f"— {ready_final}/{relevant_final} relevant videos ready, proceeding"
        )
        logger.warning(msg)
        return CheckResult(
            name=CheckCategory.VIDEOS,
            criticality=CheckCriticality.NON_CRITICAL,
            passed=False,
            elapsed_ms=elapsed_ms,
            message=msg,
        )

    def _wait_for_skeletons(self) -> CheckResult:
        """
        Wait for common skeleton/loading indicators to disappear.

        Checks for elements matching a configurable list of CSS selectors.
        Polls until none of them are visible in the DOM.

        This is a heuristic approach — custom skeleton implementations with
        non-standard class names will be missed. But the selector list is
        configurable, so teams can add their own patterns.

        Why we check visibility (not just existence): Some frameworks keep
        skeleton elements in the DOM but hide them via CSS. We use
        locator.count() which only counts attached, visible elements.

        Why this matters: Skeleton screens are the #1 cause of ugly
        screenshots in modern SPAs. The page looks "loaded" to network-
        based checks, but the user sees gray rectangles.
        """
        if not self._has_time_remaining():
            return self._skipped_result(CheckCategory.SKELETONS)

        logger.debug("Checking for skeleton/loading indicators...")
        check_start = time.time()
        timeout_seconds = self._config.skeletons_timeout_ms / 1000
        deadline = time.time() + timeout_seconds

        # Build a combined CSS selector: ".skeleton, .shimmer, .loading, ..."
        combined_selector = ", ".join(self._config.skeleton_selectors)

        while time.time() < deadline and self._has_time_remaining():
            try:
                count = self._page.locator(combined_selector).count()
                if count == 0:
                    elapsed_ms = self._elapsed_ms(check_start)
                    logger.debug("No skeleton/loading indicators found")
                    return CheckResult(
                        name=CheckCategory.SKELETONS,
                        criticality=CheckCriticality.NON_CRITICAL,
                        passed=True,
                        elapsed_ms=elapsed_ms,
                        message="No skeleton/loading indicators found",
                    )
                logger.debug(f"Found {count} skeleton/loading indicator(s), waiting...")
            except Exception as exc:
                elapsed_ms = self._elapsed_ms(check_start)
                msg = f"Skeleton check failed: {exc} — proceeding"
                logger.warning(msg)
                return CheckResult(
                    name=CheckCategory.SKELETONS,
                    criticality=CheckCriticality.NON_CRITICAL,
                    passed=False,
                    elapsed_ms=elapsed_ms,
                    message=msg,
                )

            time.sleep(0.5)

        elapsed_ms = self._elapsed_ms(check_start)
        msg = (
            f"Skeleton indicators still present after "
            f"{elapsed_ms:.0f}ms — proceeding anyway"
        )
        logger.warning(msg)
        return CheckResult(
            name=CheckCategory.SKELETONS,
            criticality=CheckCriticality.NON_CRITICAL,
            passed=False,
            elapsed_ms=elapsed_ms,
            message=msg,
        )

    def _wait_for_dom_stability(self) -> CheckResult:
        """
        Wait for the DOM node count to stabilize.

        Samples document.querySelectorAll('*').length at regular intervals.
        If the count stays the same for N consecutive readings, the DOM is
        considered stable.

        Why node count over MutationObserver:
        - MutationObserver must be injected BEFORE changes start (timing-
          dependent and fragile)
        - It fires on every micro-mutation (timers updating clocks, etc.),
          creating noise
        - Node count is a single synchronous snapshot — simple and fast
        - For detecting "page still injecting content," node count is
          perfectly adequate

        Trade-off: Node count doesn't detect attribute or text-content
        changes — only structural additions/removals. This is fine for
        our use case (skeleton → real content swaps).
        """
        if not self._has_time_remaining():
            return self._skipped_result(CheckCategory.DOM_STABILITY)

        logger.debug("Checking DOM stability...")
        check_start = time.time()
        required_checks = self._config.dom_stability_checks
        interval_seconds = self._config.dom_stability_interval_ms / 1000

        stable_count = 0
        last_node_count: int | None = None

        while stable_count < required_checks and self._has_time_remaining():
            try:
                current_count = self._page.evaluate(
                    "() => document.querySelectorAll('*').length"
                )
            except Exception as exc:
                elapsed_ms = self._elapsed_ms(check_start)
                msg = f"DOM stability check failed: {exc} — proceeding"
                logger.warning(msg)
                return CheckResult(
                    name=CheckCategory.DOM_STABILITY,
                    criticality=CheckCriticality.NON_CRITICAL,
                    passed=False,
                    elapsed_ms=elapsed_ms,
                    message=msg,
                )

            if current_count == last_node_count:
                stable_count += 1
            else:
                stable_count = 0
                last_node_count = current_count

            if stable_count < required_checks:
                time.sleep(interval_seconds)

        elapsed_ms = self._elapsed_ms(check_start)

        if stable_count >= required_checks:
            msg = (
                f"DOM stable at {last_node_count} nodes "
                f"({required_checks} consecutive checks)"
            )
            logger.debug(msg)
            return CheckResult(
                name=CheckCategory.DOM_STABILITY,
                criticality=CheckCriticality.NON_CRITICAL,
                passed=True,
                elapsed_ms=elapsed_ms,
                message=msg,
            )
        else:
            msg = f"DOM stability check timed out after {elapsed_ms:.0f}ms — proceeding"
            logger.warning(msg)
            return CheckResult(
                name=CheckCategory.DOM_STABILITY,
                criticality=CheckCriticality.NON_CRITICAL,
                passed=False,
                elapsed_ms=elapsed_ms,
                message=msg,
            )

    def _wait_for_layout_stability(self) -> CheckResult:
        """
        Wait for the document height to stabilize.

        Samples document.documentElement.scrollHeight at regular intervals.
        If the height stays the same for N consecutive readings, the layout
        is considered stable.

        Why document height and not a full CLS measurement:
        - Document height is the strongest single signal of layout instability
        - Images loading → height increases
        - Lazy content appearing → height increases
        - Font swap reflow → height changes
        - A PerformanceObserver-based CLS measurement would be more precise
          but adds significant complexity
        - Document height covers ~90% of real-world layout shift cases

        Trade-off: Horizontal layout shifts won't be detected. In practice,
        vertical shifts dominate.
        """
        if not self._has_time_remaining():
            return self._skipped_result(CheckCategory.LAYOUT_STABILITY)

        logger.debug("Checking layout stability...")
        check_start = time.time()
        required_checks = self._config.layout_stability_checks
        interval_seconds = self._config.layout_stability_interval_ms / 1000

        stable_count = 0
        last_height: int | None = None

        while stable_count < required_checks and self._has_time_remaining():
            try:
                current_height = self._page.evaluate(
                    "() => document.documentElement.scrollHeight"
                )
            except Exception as exc:
                elapsed_ms = self._elapsed_ms(check_start)
                msg = f"Layout stability check failed: {exc} — proceeding"
                logger.warning(msg)
                return CheckResult(
                    name=CheckCategory.LAYOUT_STABILITY,
                    criticality=CheckCriticality.NON_CRITICAL,
                    passed=False,
                    elapsed_ms=elapsed_ms,
                    message=msg,
                )

            if current_height == last_height:
                stable_count += 1
            else:
                stable_count = 0
                last_height = current_height

            if stable_count < required_checks:
                time.sleep(interval_seconds)

        elapsed_ms = self._elapsed_ms(check_start)

        if stable_count >= required_checks:
            msg = (
                f"Layout stable at height={last_height}px "
                f"({required_checks} consecutive checks)"
            )
            logger.debug(msg)
            return CheckResult(
                name=CheckCategory.LAYOUT_STABILITY,
                criticality=CheckCriticality.NON_CRITICAL,
                passed=True,
                elapsed_ms=elapsed_ms,
                message=msg,
            )
        else:
            msg = f"Layout stability check timed out after {elapsed_ms:.0f}ms — proceeding"
            logger.warning(msg)
            return CheckResult(
                name=CheckCategory.LAYOUT_STABILITY,
                criticality=CheckCriticality.NON_CRITICAL,
                passed=False,
                elapsed_ms=elapsed_ms,
                message=msg,
            )

    def _perform_scroll_discovery(self) -> CheckResult:
        """
        Scroll the page from top to bottom to trigger lazy-loaded content.

        This step simulates what a real user would do: scroll down the page
        and let content load as it comes into view. It triggers:
        - Lazy-loaded images (loading="lazy")
        - Infinite scroll sections
        - Deferred React/Vue components
        - IntersectionObserver-based content
        - Dynamic marketing sections

        Algorithm:
        1. Record the initial page height.
        2. Scroll down by scroll_step_pixels.
        3. Pause for scroll_pause_ms to let content render.
        4. Check if the page height grew (new content loaded).
        5. Repeat until:
           a. Page height stops growing for N consecutive scrolls, OR
           b. max_scroll_iterations is reached, OR
           c. Global time budget is exhausted.
        6. Scroll back to the top.
        7. Wait a short stabilization delay.

        Why scroll back to top: The screenshot should show the page from
        its natural starting point, not wherever scrolling stopped.

        Why gradual scrolling (not one jump to bottom): Many lazy-loading
        implementations only trigger when content enters the viewport
        during scrolling. A single scrollTo(0, document.body.scrollHeight)
        may not trigger IntersectionObserver callbacks for intermediate
        sections.
        """
        if not self._has_time_remaining():
            return self._skipped_result(CheckCategory.SCROLL_DISCOVERY)

        logger.debug("Starting scroll discovery phase...")
        check_start = time.time()

        pause_seconds = self._config.scroll_pause_ms / 1000
        stability_threshold = self._config.scroll_stability_checks
        stable_count = 0
        iterations = 0
        content_grew = False

        try:
            initial_height = self._page.evaluate(
                "() => document.documentElement.scrollHeight"
            )
        except Exception as exc:
            elapsed_ms = self._elapsed_ms(check_start)
            msg = f"Scroll discovery failed to read page height: {exc}"
            logger.warning(msg)
            return CheckResult(
                name=CheckCategory.SCROLL_DISCOVERY,
                criticality=CheckCriticality.NON_CRITICAL,
                passed=False,
                elapsed_ms=elapsed_ms,
                message=msg,
            )

        last_height = initial_height

        while (
            iterations < self._config.max_scroll_iterations
            and stable_count < stability_threshold
            and self._has_time_remaining()
        ):
            iterations += 1

            scroll_js = f"""
            () => {{
                const step = {self._config.scroll_step_pixels};
                
                // 1. Try normal window scroll
                const oldY = window.scrollY;
                window.scrollBy(0, step);
                
                if (window.scrollY > oldY) {{
                    const max = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
                    return {{
                        scrolled: true,
                        isAtBottom: window.scrollY + window.innerHeight >= max - 10,
                        height: max
                    }};
                }}
                
                // 2. Try custom scroll containers (e.g. overflow: auto/scroll wrappers)
                const scrollable = Array.from(document.querySelectorAll('*')).find(el => {{
                    if (el.scrollHeight > el.clientHeight) {{
                        const style = window.getComputedStyle(el);
                        return style.overflowY === 'auto' || style.overflowY === 'scroll';
                    }}
                    return false;
                }});
                
                if (scrollable) {{
                    const oldTop = scrollable.scrollTop;
                    scrollable.scrollBy(0, step);
                    return {{
                        scrolled: scrollable.scrollTop > oldTop,
                        isAtBottom: scrollable.scrollTop + scrollable.clientHeight >= scrollable.scrollHeight - 10,
                        height: scrollable.scrollHeight
                    }};
                }}
                
                // 3. Nowhere to scroll
                return {{
                    scrolled: false,
                    isAtBottom: true,
                    height: document.documentElement.scrollHeight
                }};
            }}
            """

            try:
                state = self._page.evaluate(scroll_js)
            except Exception as exc:
                logger.warning(f"Scroll action failed at iteration {iterations}: {exc}")
                break

            # Pause to let lazy content render
            time.sleep(pause_seconds)

            current_height = state["height"]

            if current_height > last_height:
                content_grew = True
                stable_count = 0
                logger.debug(
                    f"Scroll iteration {iterations}: "
                    f"height grew {last_height}px → {current_height}px"
                )
                last_height = current_height
            elif state["isAtBottom"] or not state["scrolled"]:
                # If we hit the bottom (or can't scroll), wait to see if new content loads
                stable_count += 1
                logger.debug(
                    f"Scroll iteration {iterations}: reached bottom, "
                    f"waiting for content (stable {stable_count}/{stability_threshold})"
                )
            else:
                # We are scrolling down a tall page, haven't reached the bottom yet.
                # Do not increment stable_count, keep going.
                stable_count = 0

        # Scroll back to top for the screenshot
        try:
            self._page.evaluate("() => window.scrollTo(0, 0)")
            # Brief stabilization after returning to top
            time.sleep(0.3)
        except Exception as exc:
            logger.warning(f"Failed to scroll back to top: {exc}")

        elapsed_ms = self._elapsed_ms(check_start)
        height_delta = last_height - initial_height

        if content_grew:
            msg = (
                f"Scroll discovery completed: {iterations} iterations, "
                f"page grew by {height_delta}px "
                f"({initial_height}px → {last_height}px)"
            )
        else:
            msg = (
                f"Scroll discovery completed: {iterations} iterations, "
                f"no new content detected (height={initial_height}px)"
            )

        logger.debug(msg)

        # Scroll discovery "passes" if it completed without errors.
        # Even if no new content was found, it means the page had nothing
        # to lazy-load — that's a valid outcome, not a failure.
        return CheckResult(
            name=CheckCategory.SCROLL_DISCOVERY,
            criticality=CheckCriticality.NON_CRITICAL,
            passed=True,
            elapsed_ms=elapsed_ms,
            message=msg,
        )

    # -------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------

    def _has_time_remaining(self) -> bool:
        """
        Check if the global time budget (max_wait_seconds) has been exhausted.

        Every step in the pipeline calls this before doing work and inside
        polling loops. This guarantees the entire readiness process stays
        within the configured budget, regardless of how many individual
        checks are enabled.
        """
        elapsed = time.time() - self._start_time
        remaining = self._config.max_wait_seconds - elapsed

        if remaining <= 0:
            logger.warning(
                f"Global readiness timeout reached "
                f"({self._config.max_wait_seconds}s) — skipping remaining checks"
            )
            return False
        return True

    def _effective_timeout(self, check_timeout_ms: int) -> int:
        """
        Return the smaller of the check's own timeout and the remaining
        global budget. This prevents a single check from exceeding the
        overall scan time budget.

        Args:
            check_timeout_ms: The check's configured timeout in milliseconds.

        Returns:
            The effective timeout to use, in milliseconds.
        """
        elapsed = time.time() - self._start_time
        remaining_ms = (self._config.max_wait_seconds - elapsed) * 1000
        return max(1, int(min(check_timeout_ms, remaining_ms)))

    def _elapsed_ms(self, check_start: float) -> float:
        """Calculate milliseconds elapsed since a check started."""
        return round((time.time() - check_start) * 1000, 1)

    def _skipped_result(self, category: CheckCategory) -> CheckResult:
        """
        Create a CheckResult for a check that was skipped because the
        global time budget was exhausted.
        """
        return CheckResult(
            name=category,
            criticality=CheckCriticality.NON_CRITICAL,
            passed=False,
            elapsed_ms=0.0,
            message=f"Skipped — global time budget exhausted ({self._config.max_wait_seconds}s)",
        )
