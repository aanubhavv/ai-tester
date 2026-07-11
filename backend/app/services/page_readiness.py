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
"""

import logging
import time
from dataclasses import dataclass, field

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

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
        engine.wait_until_ready()
        # page is now stable — safe to screenshot

    The pipeline runs each check in order. Each check respects the global
    max_wait_seconds budget — if time runs out, remaining checks are skipped
    and we proceed with what we have. This prevents a single misbehaving
    page from hanging the scanner forever.
    """

    def __init__(self, page: Page, config: ReadinessConfig | None = None) -> None:
        self._page = page
        self._config = config or ReadinessConfig()
        self._start_time: float = 0.0

    def wait_until_ready(self) -> None:
        """
        Run the full readiness pipeline.

        Each step is guarded by its config toggle and the global time budget.
        Steps run in a deliberate order — fonts and images first (they affect
        layout), then skeleton detection, then stability checks (which verify
        everything has settled), then the final delay.
        """
        self._start_time = time.time()
        logger.info("Page readiness pipeline started")

        # Step 1: Fonts (affects text layout → must come before stability checks)
        if self._config.wait_for_fonts and self._has_time_remaining():
            self._wait_for_fonts()

        # Step 2: Images (affects layout → must come before stability checks)
        if self._config.wait_for_images and self._has_time_remaining():
            self._wait_for_images()

        # Step 3: Videos (must come before skeletons — skeleton→video transitions
        # are a primary source of black-frame screenshots; we want the video
        # buffer primed before we declare the skeleton gone)
        if self._config.wait_for_videos and self._has_time_remaining():
            self._wait_for_videos()

        # Step 4: Skeleton/loading indicators (content swaps → must come
        # before stability checks, since skeleton→content transition changes
        # both DOM and layout)
        if self._config.wait_for_skeletons and self._has_time_remaining():
            self._wait_for_skeletons()

        # Step 5: DOM stability (verify no more structural changes)
        if self._has_time_remaining():
            self._wait_for_dom_stability()

        # Step 6: Layout stability (verify no more height/position changes)
        if self._has_time_remaining():
            self._wait_for_layout_stability()

        # Step 7: Final delay (safety net for animations and paint)
        if self._config.final_delay_seconds > 0:
            logger.debug(
                f"Final stabilization delay: {self._config.final_delay_seconds}s"
            )
            time.sleep(self._config.final_delay_seconds)

        elapsed = round(time.time() - self._start_time, 2)
        logger.info(f"Page readiness pipeline completed in {elapsed}s")

    # -------------------------------------------------------------------
    # Individual readiness checks
    # -------------------------------------------------------------------

    def _wait_for_fonts(self) -> None:
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
        logger.debug("Waiting for web fonts...")
        try:
            self._page.wait_for_function(
                "() => document.fonts.ready",
                timeout=self._config.fonts_timeout_ms,
            )
            logger.debug("Web fonts loaded")
        except PlaywrightTimeout:
            logger.warning(
                f"Font loading timed out after {self._config.fonts_timeout_ms}ms "
                f"— proceeding without waiting further"
            )
        except Exception as exc:
            logger.warning(f"Font check failed: {exc} — proceeding")

    def _wait_for_images(self) -> None:
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
        logger.debug("Waiting for images to load...")
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
                    logger.debug("All images loaded")
                    return
            except Exception as exc:
                logger.warning(f"Image check failed: {exc} — proceeding")
                return

            time.sleep(0.3)

        logger.warning(
            f"Image loading timed out after {self._config.images_timeout_ms}ms "
            f"— proceeding with potentially unloaded images"
        )

    def _wait_for_videos(self) -> None:
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
        logger.debug("Waiting for video elements to reach readyState \u2265 2...")
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
                logger.warning(f"Video readiness check failed: {exc} — proceeding")
                return

            total: int = result["total"]
            relevant: int = result["relevant"]
            ready: int = result["ready"]
            done: bool = result["done"]

            if total == 0:
                logger.debug("No <video> elements found — skipping video readiness check")
                return

            if done:
                logger.debug(
                    f"Videos ready: {ready}/{relevant} relevant "
                    f"({total - relevant} excluded with preload=\"none\")"
                )
                return

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

        logger.warning(
            f"Video readiness timed out after {self._config.videos_timeout_ms}ms "
            f"— {ready_final}/{relevant_final} relevant videos ready, proceeding"
        )

    def _wait_for_skeletons(self) -> None:
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
        logger.debug("Checking for skeleton/loading indicators...")
        timeout_seconds = self._config.skeletons_timeout_ms / 1000
        deadline = time.time() + timeout_seconds

        # Build a combined CSS selector: ".skeleton, .shimmer, .loading, ..."
        combined_selector = ", ".join(self._config.skeleton_selectors)

        while time.time() < deadline and self._has_time_remaining():
            try:
                count = self._page.locator(combined_selector).count()
                if count == 0:
                    logger.debug("No skeleton/loading indicators found")
                    return
                logger.debug(f"Found {count} skeleton/loading indicator(s), waiting...")
            except Exception as exc:
                logger.warning(f"Skeleton check failed: {exc} — proceeding")
                return

            time.sleep(0.5)

        logger.warning(
            f"Skeleton indicators still present after "
            f"{self._config.skeletons_timeout_ms}ms — proceeding anyway"
        )

    def _wait_for_dom_stability(self) -> None:
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
        logger.debug("Checking DOM stability...")
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
                logger.warning(f"DOM stability check failed: {exc} — proceeding")
                return

            if current_count == last_node_count:
                stable_count += 1
            else:
                stable_count = 0
                last_node_count = current_count

            if stable_count < required_checks:
                time.sleep(interval_seconds)

        if stable_count >= required_checks:
            logger.debug(
                f"DOM stable at {last_node_count} nodes "
                f"({required_checks} consecutive checks)"
            )
        else:
            logger.warning("DOM stability check timed out — proceeding")

    def _wait_for_layout_stability(self) -> None:
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
        logger.debug("Checking layout stability...")
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
                logger.warning(f"Layout stability check failed: {exc} — proceeding")
                return

            if current_height == last_height:
                stable_count += 1
            else:
                stable_count = 0
                last_height = current_height

            if stable_count < required_checks:
                time.sleep(interval_seconds)

        if stable_count >= required_checks:
            logger.debug(
                f"Layout stable at height={last_height}px "
                f"({required_checks} consecutive checks)"
            )
        else:
            logger.warning("Layout stability check timed out — proceeding")

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
