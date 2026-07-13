"""
Website Analysis Engine
=======================

This module answers: "What is on this page, and how is it structured?"

It operates on a Playwright Page object that has ALREADY been stabilised by
the PageReadinessEngine. It never navigates, never waits for readiness, and
never takes screenshots — those are BrowserService's responsibilities.

Two top-level objects live here:

EventCollector
    Must be created BEFORE page.goto() is called. It registers Playwright
    event hooks on the page object so that console messages and failed network
    requests are captured during navigation. After navigation completes, the
    collected events are handed to AnalysisService.

    Why event hooks and not post-load queries?
    Console events and requestfailed events are streaming — they fire exactly
    once, during page load. There is no DOM property to query after the fact.
    The only way to capture them is to be listening before they fire.

AnalysisService
    Receives a stabilised Page object and an EventCollector. Runs all 10
    analysis categories, each isolated in its own method. Assembles and
    returns a single AnalysisResult dataclass.

    Why dataclasses (not Pydantic) for the result?
    The result is an internal domain object. It never crosses the HTTP
    boundary directly — the endpoint converts it to an AnalysisResponse
    Pydantic model for serialisation. Using a dataclass keeps this module
    independent of the API layer and avoids unnecessary validation overhead
    for internal data.

JavaScript batching strategy
    Each category runs exactly ONE page.evaluate() call. Every evaluate()
    is an IPC round-trip from the Python process to the browser process.
    Batching all related fields into one JS function dramatically reduces
    latency compared to one evaluate() per field.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from playwright.sync_api import Page, ConsoleMessage, Request

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event data containers (internal — not exposed to the API layer directly)
# ---------------------------------------------------------------------------

@dataclass
class ConsoleEvent:
    type: str
    text: str
    timestamp: Optional[float]  # Unix seconds


@dataclass
class NetworkFailureEvent:
    url: str
    method: str
    failure_reason: Optional[str]
    timestamp: Optional[float]  # Unix seconds


# ---------------------------------------------------------------------------
# EventCollector
# ---------------------------------------------------------------------------

class EventCollector:
    """
    Captures streaming page events that can only be observed during navigation.

    MUST be instantiated immediately after browser.new_page() and BEFORE
    page.goto(). The constructor registers Playwright event hooks; any events
    that fire before the hooks are registered are lost permanently.

    Usage:
        page = browser.new_page()
        collector = EventCollector(page)   # hooks attached here
        page.goto(url)                     # events captured here
        # ... readiness engine runs ...
        analysis = AnalysisService(page, collector).run()

    Thread safety: Playwright's sync API calls the handlers synchronously
    on the same thread as the page, so no locking is needed.
    """

    def __init__(self, page: Page) -> None:
        self._console_events: list[ConsoleEvent] = []
        self._network_failures: list[NetworkFailureEvent] = []
        self._start_time = time.time()

        # Register hooks immediately on construction.
        # Playwright guarantees these are called before any Python code
        # between goto() and the event resolving.
        page.on("console", self._on_console)
        page.on("requestfailed", self._on_request_failed)

        logger.debug("EventCollector: hooks registered on page")

    def _on_console(self, msg: ConsoleMessage) -> None:
        """
        Handler for browser console events.

        We capture only errors and warnings — log/debug/info messages
        are extremely noisy (React DevTools, analytics SDKs, etc.) and
        add no value for QA analysis.

        msg.text() can raise if the message contains a non-serialisable
        value (e.g. a circular reference). We guard with a try/except.
        """
        msg_type = msg.type  # "error", "warning", "log", "debug", etc.
        if msg_type not in ("error", "warning"):
            return

        try:
            text = msg.text
        except Exception:
            text = "<unreadable console message>"

        self._console_events.append(
            ConsoleEvent(
                type=msg_type,
                text=text,
                timestamp=time.time(),
            )
        )

    def _on_request_failed(self, request: Request) -> None:
        """
        Handler for network requests that failed at the transport layer.

        Note: HTTP 4xx/5xx responses are NOT failures here — Playwright
        considers those successful requests (the server responded, just
        with an error code). A "failed" request is one where no HTTP
        response was received at all: DNS failure, connection refused,
        SSL error, etc.

        request.failure() returns a dict with a "errorText" key, or None
        if somehow called on a non-failed request.
        """
        failure_info = request.failure
        failure_reason = failure_info if isinstance(failure_info, str) else None

        self._network_failures.append(
            NetworkFailureEvent(
                url=request.url,
                method=request.method,
                failure_reason=failure_reason,
                timestamp=time.time(),
            )
        )

    @property
    def console_errors(self) -> list[ConsoleEvent]:
        return [e for e in self._console_events if e.type == "error"]

    @property
    def console_warnings(self) -> list[ConsoleEvent]:
        return [e for e in self._console_events if e.type == "warning"]

    @property
    def network_failures(self) -> list[NetworkFailureEvent]:
        return list(self._network_failures)


# ---------------------------------------------------------------------------
# Analysis result dataclasses (internal domain objects)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MetadataResult:
    title: str
    description: Optional[str]
    canonical_url: Optional[str]
    language: Optional[str]
    charset: Optional[str]
    current_url: str


@dataclass(frozen=True)
class HeadingResult:
    h1: list[str]
    h2: list[str]
    h3: list[str]
    h1_count: int
    h2_count: int
    h3_count: int


@dataclass(frozen=True)
class ImageResult:
    total: int
    missing_alt: int
    empty_alt: int
    broken: int
    lazy_loaded: int


@dataclass(frozen=True)
class LinkResult:
    total: int
    internal: int
    external: int
    no_href: int
    duplicate_count: int


@dataclass(frozen=True)
class FormResult:
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


@dataclass(frozen=True)
class AssetResult:
    scripts: int
    stylesheets: int
    fonts: int
    videos: int
    iframes: int
    svgs: int
    canvases: int


@dataclass(frozen=True)
class StorageResult:
    cookies: int
    local_storage: int
    session_storage: int


@dataclass(frozen=True)
class DomResult:
    total_nodes: int
    height: int
    width: int
    buttons: int
    tables: int
    lists: int
    paragraphs: int


@dataclass(frozen=True)
class ElementLayout:
    tag: str
    id: Optional[str]
    classes: list[str]
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class LayoutResult:
    elements: list[ElementLayout]


@dataclass(frozen=True)
class AnalysisResult:
    """
    The complete page analysis result.

    This is the return type of AnalysisService.run(). It is an internal
    domain object — the API endpoint converts it to an AnalysisResponse
    Pydantic model before serialisation.
    """
    metadata: MetadataResult
    headings: HeadingResult
    images: ImageResult
    links: LinkResult
    forms: FormResult
    assets: AssetResult
    storage: StorageResult
    dom: DomResult
    console_errors: list[ConsoleEvent]
    console_warnings: list[ConsoleEvent]
    network_failures: list[NetworkFailureEvent]
    layout: LayoutResult


# ---------------------------------------------------------------------------
# Analysis Service
# ---------------------------------------------------------------------------

class AnalysisService:
    """
    Extracts structured data from a fully-loaded Playwright page.

    Each public method corresponds to one analysis category. Each method
    issues exactly one page.evaluate() call, batching all related field
    extraction into a single JavaScript function.

    The service is stateless across calls — create a new instance per scan.

    Args:
        page:      A Playwright Page that has already been navigated and
                   stabilised by PageReadinessEngine.
        collector: An EventCollector that captured streaming events during
                   navigation. Pass None only in unit tests.
    """

    def __init__(self, page: Page, collector: EventCollector | None = None) -> None:
        self._page = page
        self._collector = collector

    def run(self) -> AnalysisResult:
        """
        Execute all analysis categories in sequence and return the result.

        Order is designed for efficiency — categories that touch similar DOM
        regions are grouped. Each call is independent; a failure in one
        category logs a warning and uses a safe fallback rather than aborting
        the whole analysis.
        """
        start = time.time()
        logger.info("Analysis engine started")

        result = AnalysisResult(
            metadata=self._analyse_metadata(),
            headings=self._analyse_headings(),
            images=self._analyse_images(),
            links=self._analyse_links(),
            forms=self._analyse_forms(),
            assets=self._analyse_assets(),
            storage=self._analyse_storage(),
            dom=self._analyse_dom(),
            console_errors=self._collector.console_errors if self._collector else [],
            console_warnings=self._collector.console_warnings if self._collector else [],
            network_failures=self._collector.network_failures if self._collector else [],
            layout=self._analyse_layout(),
        )

        elapsed = round(time.time() - start, 3)
        logger.info(f"Analysis engine completed in {elapsed}s")
        return result

    # -------------------------------------------------------------------
    # 1. Metadata
    # -------------------------------------------------------------------

    def _analyse_metadata(self) -> MetadataResult:
        """
        Collect core page identity fields in a single evaluate() call.

        We use querySelector rather than document.title because querySelector
        also captures pages that use Open Graph meta tags as the primary title
        source — though we read both and prefer the <title> element.

        document.characterSet is the resolved charset (always UTF-8 in modern
        browsers even if no meta charset is declared), while we also check the
        explicit <meta charset> declaration for reporting accuracy.
        """
        logger.debug("Collecting metadata...")
        try:
            raw = self._page.evaluate("""
            () => {
                const getMeta = (name) => {
                    const el = document.querySelector(
                        `meta[name="${name}"], meta[property="${name}"]`
                    );
                    return el ? el.getAttribute('content') : null;
                };

                const canonical = document.querySelector('link[rel="canonical"]');
                const charsetEl = document.querySelector('meta[charset]');

                return {
                    title: document.title || null,
                    description: getMeta('description') || getMeta('og:description'),
                    canonical_url: canonical ? canonical.getAttribute('href') : null,
                    language: document.documentElement.lang || null,
                    charset: charsetEl
                        ? charsetEl.getAttribute('charset')
                        : document.characterSet,
                    current_url: window.location.href,
                };
            }
            """)
            logger.debug(f"Metadata collected: title='{raw.get('title')}'")
            return MetadataResult(
                title=raw.get("title") or "No title found",
                description=raw.get("description"),
                canonical_url=raw.get("canonical_url"),
                language=raw.get("language"),
                charset=raw.get("charset"),
                current_url=raw.get("current_url", self._page.url),
            )
        except Exception as exc:
            logger.warning(f"Metadata analysis failed: {exc}")
            return MetadataResult(
                title="Unknown",
                description=None,
                canonical_url=None,
                language=None,
                charset=None,
                current_url=self._page.url,
            )

    # -------------------------------------------------------------------
    # 2. Headings
    # -------------------------------------------------------------------

    def _analyse_headings(self) -> HeadingResult:
        """
        Collect all H1/H2/H3 text content in a single evaluate() call.

        innerText (not textContent) is used because it reflects the rendered
        text — it skips hidden elements and collapses whitespace the way a
        human would read it. This matters for headings that contain <span>
        or <img alt="..."> children.
        """
        logger.debug("Collecting headings...")
        try:
            raw = self._page.evaluate("""
            () => {
                const texts = (selector) =>
                    Array.from(document.querySelectorAll(selector))
                         .map(el => el.innerText.trim())
                         .filter(t => t.length > 0);

                const h1 = texts('h1');
                const h2 = texts('h2');
                const h3 = texts('h3');

                return {
                    h1, h2, h3,
                    h1_count: h1.length,
                    h2_count: h2.length,
                    h3_count: h3.length,
                };
            }
            """)
            logger.debug(
                f"Headings: {raw['h1_count']} H1, "
                f"{raw['h2_count']} H2, {raw['h3_count']} H3"
            )
            return HeadingResult(**raw)
        except Exception as exc:
            logger.warning(f"Heading analysis failed: {exc}")
            return HeadingResult(h1=[], h2=[], h3=[], h1_count=0, h2_count=0, h3_count=0)

    # -------------------------------------------------------------------
    # 3. Images
    # -------------------------------------------------------------------

    def _analyse_images(self) -> ImageResult:
        """
        Collect image accessibility and loading metrics.

        broken image detection uses naturalWidth === 0 && complete === true.
        An image is "complete" (loaded/attempted) but has no decoded pixels
        only when the resource is truly broken. This is a client-side
        heuristic — it misses images that returned a valid HTTP response
        but contained corrupt data (rare), and it misses images that haven't
        started loading yet (those will have complete === false instead).

        We do NOT make external HTTP requests to validate image URLs.
        """
        logger.debug("Collecting image metrics...")
        try:
            raw = self._page.evaluate("""
            () => {
                const imgs = Array.from(document.querySelectorAll('img'));

                let missing_alt = 0;
                let empty_alt = 0;
                let broken = 0;
                let lazy_loaded = 0;

                for (const img of imgs) {
                    // hasAttribute catches missing attribute entirely
                    if (!img.hasAttribute('alt')) {
                        missing_alt++;
                    } else if (img.alt.trim() === '') {
                        empty_alt++;
                    }

                    // naturalWidth=0 + complete=true = resource failed to decode
                    if (img.complete && img.naturalWidth === 0) {
                        broken++;
                    }

                    if (img.loading === 'lazy') {
                        lazy_loaded++;
                    }
                }

                return {
                    total: imgs.length,
                    missing_alt,
                    empty_alt,
                    broken,
                    lazy_loaded,
                };
            }
            """)
            logger.debug(
                f"Images: {raw['total']} total, "
                f"{raw['missing_alt']} missing alt, {raw['broken']} broken"
            )
            return ImageResult(**raw)
        except Exception as exc:
            logger.warning(f"Image analysis failed: {exc}")
            return ImageResult(total=0, missing_alt=0, empty_alt=0, broken=0, lazy_loaded=0)

    # -------------------------------------------------------------------
    # 4. Links
    # -------------------------------------------------------------------

    def _analyse_links(self) -> LinkResult:
        """
        Analyse all anchor tags on the page.

        Internal vs external is determined by comparing the link's hostname
        to window.location.hostname. This is purely client-side and handles
        relative URLs correctly because the browser has already resolved them
        against the page origin.

        Duplicate detection normalises hrefs by stripping trailing slashes
        and lowercasing, then counts hrefs that appear more than once.
        """
        logger.debug("Collecting link metrics...")
        try:
            raw = self._page.evaluate("""
            () => {
                const anchors = Array.from(document.querySelectorAll('a'));
                const origin = window.location.hostname;

                let internal = 0;
                let external = 0;
                let no_href = 0;
                const seen = {};
                let duplicate_count = 0;

                for (const a of anchors) {
                    const href = a.getAttribute('href');

                    if (!href || href.trim() === '') {
                        no_href++;
                        continue;
                    }

                    // Resolve relative URLs via the browser's URL parser
                    let hostname;
                    try {
                        const abs = new URL(href, window.location.href);
                        hostname = abs.hostname;

                        // Normalise for duplicate detection
                        const normalised = abs.href.replace(/\\/+$/, '').toLowerCase();
                        seen[normalised] = (seen[normalised] || 0) + 1;
                        if (seen[normalised] === 2) duplicate_count++;
                    } catch (_) {
                        // Malformed href (e.g. "javascript:void(0)")
                        no_href++;
                        continue;
                    }

                    if (hostname === origin || hostname === '') {
                        internal++;
                    } else {
                        external++;
                    }
                }

                return {
                    total: anchors.length,
                    internal,
                    external,
                    no_href,
                    duplicate_count,
                };
            }
            """)
            logger.debug(
                f"Links: {raw['total']} total, "
                f"{raw['internal']} internal, {raw['external']} external"
            )
            return LinkResult(**raw)
        except Exception as exc:
            logger.warning(f"Link analysis failed: {exc}")
            return LinkResult(total=0, internal=0, external=0, no_href=0, duplicate_count=0)

    # -------------------------------------------------------------------
    # 5. Forms
    # -------------------------------------------------------------------

    def _analyse_forms(self) -> FormResult:
        """
        Analyse all form elements and their input fields.

        We count inputs by their 'type' attribute (defaulting to 'text' when
        absent, which matches browser behaviour). We do NOT submit or interact
        with forms in any way.

        required: counts any field with the required attribute (applies to
        input, textarea, and select).
        """
        logger.debug("Collecting form metrics...")
        try:
            raw = self._page.evaluate("""
            () => {
                const forms = document.querySelectorAll('form');
                const inputs = Array.from(document.querySelectorAll('input'));
                const textareas = document.querySelectorAll('textarea');
                const selects = document.querySelectorAll('select');
                const buttons = document.querySelectorAll('button, input[type="submit"], input[type="button"]');

                // Count inputs by type (default type is 'text')
                const typeCounts = {};
                for (const inp of inputs) {
                    const t = (inp.getAttribute('type') || 'text').toLowerCase();
                    typeCounts[t] = (typeCounts[t] || 0) + 1;
                }

                // Count required on input, textarea, select
                const allFields = [
                    ...inputs,
                    ...Array.from(textareas),
                    ...Array.from(selects),
                ];
                const required = allFields.filter(el => el.hasAttribute('required')).length;

                return {
                    total: forms.length,
                    inputs: inputs.length,
                    text: typeCounts['text'] || 0,
                    email: typeCounts['email'] || 0,
                    password: typeCounts['password'] || 0,
                    checkbox: typeCounts['checkbox'] || 0,
                    radio: typeCounts['radio'] || 0,
                    textarea: textareas.length,
                    select: selects.length,
                    buttons: buttons.length,
                    required,
                };
            }
            """)
            logger.debug(f"Forms: {raw['total']} forms, {raw['inputs']} inputs")
            return FormResult(**raw)
        except Exception as exc:
            logger.warning(f"Form analysis failed: {exc}")
            return FormResult(
                total=0, inputs=0, text=0, email=0, password=0,
                checkbox=0, radio=0, textarea=0, select=0, buttons=0, required=0,
            )

    # -------------------------------------------------------------------
    # 6. Assets
    # -------------------------------------------------------------------

    def _analyse_assets(self) -> AssetResult:
        """
        Count page assets by element type.

        fonts: counts <link rel="preload" as="font"> and
               <link rel="stylesheet"> that reference font files (.woff, .woff2,
               .ttf, .otf). This is a heuristic — fonts loaded via @font-face
               in CSS are not counted here without a more expensive CSS parse.

        scripts: external scripts only (src attribute present) — inline
                 <script> blocks are not counted as "assets".

        stylesheets: <link rel="stylesheet"> elements only.
        """
        logger.debug("Collecting asset metrics...")
        try:
            raw = self._page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script[src]').length;

                const stylesheets = document.querySelectorAll(
                    'link[rel="stylesheet"]'
                ).length;

                // Font assets: preload hints + direct font file links
                const fontExtensions = /\\.(woff2?|ttf|otf|eot)(\\?.*)?$/i;
                const allLinks = Array.from(document.querySelectorAll('link'));
                const fonts = allLinks.filter(link => {
                    const rel = link.getAttribute('rel') || '';
                    const href = link.getAttribute('href') || '';
                    return (
                        (rel === 'preload' && link.getAttribute('as') === 'font') ||
                        fontExtensions.test(href)
                    );
                }).length;

                const videos = document.querySelectorAll('video').length;
                const iframes = document.querySelectorAll('iframe').length;
                const svgs = document.querySelectorAll('svg').length;
                const canvases = document.querySelectorAll('canvas').length;

                return { scripts, stylesheets, fonts, videos, iframes, svgs, canvases };
            }
            """)
            logger.debug(
                f"Assets: {raw['scripts']} scripts, "
                f"{raw['stylesheets']} stylesheets, {raw['videos']} videos"
            )
            return AssetResult(**raw)
        except Exception as exc:
            logger.warning(f"Asset analysis failed: {exc}")
            return AssetResult(
                scripts=0, stylesheets=0, fonts=0,
                videos=0, iframes=0, svgs=0, canvases=0,
            )

    # -------------------------------------------------------------------
    # 7. Browser Storage
    # -------------------------------------------------------------------

    def _analyse_storage(self) -> StorageResult:
        """
        Count browser storage entries — never return values.

        Cookies are counted by splitting document.cookie on ';' and filtering
        empty strings. This only counts cookies accessible to JavaScript
        (HttpOnly cookies are invisible here — they exist but can't be read,
        which is the correct security behaviour).

        localStorage and sessionStorage .length is a synchronous O(1) property.
        """
        logger.debug("Collecting storage metrics...")
        try:
            raw = self._page.evaluate("""
            () => {
                const cookieCount = document.cookie
                    ? document.cookie.split(';').filter(c => c.trim()).length
                    : 0;

                let localCount = 0;
                let sessionCount = 0;
                try { localCount = localStorage.length; } catch (_) {}
                try { sessionCount = sessionStorage.length; } catch (_) {}

                return {
                    cookies: cookieCount,
                    local_storage: localCount,
                    session_storage: sessionCount,
                };
            }
            """)
            logger.debug(
                f"Storage: {raw['cookies']} cookies, "
                f"{raw['local_storage']} localStorage keys"
            )
            return StorageResult(**raw)
        except Exception as exc:
            logger.warning(f"Storage analysis failed: {exc}")
            return StorageResult(cookies=0, local_storage=0, session_storage=0)

    # -------------------------------------------------------------------
    # 8. DOM Statistics
    # -------------------------------------------------------------------

    def _analyse_dom(self) -> DomResult:
        """
        Collect structural DOM metrics in a single evaluate() call.

        querySelectorAll('*').length counts every element node in the document,
        including <head> contents. This is a standard proxy for DOM complexity.

        scrollHeight / scrollWidth are the total dimensions of the document
        content, not the viewport. These tell us how tall/wide the page actually
        is after all lazy content has loaded.

        ul, ol, dl are all counted as "lists" — they all represent enumerated
        content structures from an accessibility perspective.
        """
        logger.debug("Collecting DOM statistics...")
        try:
            raw = self._page.evaluate("""
            () => ({
                total_nodes: document.querySelectorAll('*').length,
                height: document.documentElement.scrollHeight,
                width: document.documentElement.scrollWidth,
                buttons: document.querySelectorAll(
                    'button, input[type="submit"], input[type="button"], [role="button"]'
                ).length,
                tables: document.querySelectorAll('table').length,
                lists: document.querySelectorAll('ul, ol, dl').length,
                paragraphs: document.querySelectorAll('p').length,
            })
            """)
            logger.debug(
                f"DOM: {raw['total_nodes']} nodes, "
                f"height={raw['height']}px"
            )
            return DomResult(**raw)
        except Exception as exc:
            logger.warning(f"DOM analysis failed: {exc}")
            return DomResult(
                total_nodes=0, height=0, width=0,
                buttons=0, tables=0, lists=0, paragraphs=0,
            )

    # -------------------------------------------------------------------
    # 9. Layout Mapping
    # -------------------------------------------------------------------

    def _analyse_layout(self) -> LayoutResult:
        """
        Extract the bounding boxes of major elements on the page.

        We collect bounding boxes for elements that have an ID or class,
        as these are the elements most likely to be targeted by 
        `ignored_selectors` in a visual comparison.

        Filtering by width/height > 0 ensures we don't store hidden elements.
        """
        logger.debug("Collecting layout mapping...")
        try:
            raw = self._page.evaluate("""
            () => {
                const elements = document.querySelectorAll('*');
                const layout = [];
                for (const el of elements) {
                    if (!el.id && el.classList.length === 0) continue;
                    
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) continue;

                    layout.push({
                        tag: el.tagName.toLowerCase(),
                        id: el.id || null,
                        classes: Array.from(el.classList),
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    });
                }
                return { elements: layout };
            }
            """)
            
            elements = [ElementLayout(**el) for el in raw.get("elements", [])]
            logger.debug(f"Layout mapping: {len(elements)} elements")
            return LayoutResult(elements=elements)
        except Exception as exc:
            logger.warning(f"Layout analysis failed: {exc}")
            return LayoutResult(elements=[])


# ---------------------------------------------------------------------------
# Converter: AnalysisResult → AnalysisResponse (Pydantic)
# ---------------------------------------------------------------------------

def to_analysis_response(result: AnalysisResult):
    """
    Convert an internal AnalysisResult dataclass to an AnalysisResponse
    Pydantic model ready for API serialisation.

    This is a module-level function — not a method on AnalysisService or
    AnalysisResult — because conversion is a pure transformation between two
    layers. Keeping it here avoids circular imports (schemas can't import
    services; services importing schemas is fine).

    The import is deferred inside the function to keep the service layer
    independent at module load time. The actual import happens only when a
    scan completes and conversion is required.
    """
    from app.schemas.analysis import (
        AnalysisResponse,
        MetadataSchema,
        HeadingSchema,
        ImageSchema,
        LinkSchema,
        FormSchema,
        AssetSchema,
        StorageSchema,
        DomSchema,
        ConsoleSchema,
        ConsoleMessageSchema,
        NetworkSchema,
        NetworkFailureSchema,
        LayoutSchema,
        ElementLayoutSchema,
    )

    return AnalysisResponse(
        metadata=MetadataSchema(**result.metadata.__dict__),
        headings=HeadingSchema(**result.headings.__dict__),
        images=ImageSchema(**result.images.__dict__),
        links=LinkSchema(**result.links.__dict__),
        forms=FormSchema(**result.forms.__dict__),
        assets=AssetSchema(**result.assets.__dict__),
        storage=StorageSchema(**result.storage.__dict__),
        dom=DomSchema(**result.dom.__dict__),
        console=ConsoleSchema(
            errors=[
                ConsoleMessageSchema(
                    type=e.type, text=e.text, timestamp=e.timestamp
                )
                for e in result.console_errors
            ],
            warnings=[
                ConsoleMessageSchema(
                    type=e.type, text=e.text, timestamp=e.timestamp
                )
                for e in result.console_warnings
            ],
        ),
        network=NetworkSchema(
            failed_requests=[
                NetworkFailureSchema(
                    url=f.url,
                    method=f.method,
                    failure_reason=f.failure_reason,
                    timestamp=f.timestamp,
                )
                for f in result.network_failures
            ]
        ),
        layout=LayoutSchema(
            elements=[
                ElementLayoutSchema(
                    tag=el.tag,
                    id=el.id,
                    classes=el.classes,
                    x=el.x,
                    y=el.y,
                    width=el.width,
                    height=el.height,
                )
                for el in result.layout.elements
            ]
        ),
    )
