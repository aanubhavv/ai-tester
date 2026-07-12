"""
Readiness Result Models
=======================

Structured types for the Page Readiness Engine's output.

This module exists separately from page_readiness.py because these types
are consumed by multiple layers:
- page_readiness.py (produces ReadinessResult)
- browser_service.py (inspects ReadinessResult to decide continue/abort)
- schemas/scan.py (converts ReadinessResult to API response models)

Placing them here avoids circular imports and keeps each module focused
on a single responsibility.

All dataclasses are frozen (immutable) because readiness results are
facts about a completed pipeline run — they should never be modified
after creation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CheckCategory(str, Enum):
    """
    Names for each readiness check in the pipeline.

    Inherits from str so the enum serialises to a plain string in JSON
    (e.g., "fonts" instead of "CheckCategory.FONTS"). This matters when
    the values flow into API responses via Pydantic.

    Each value is a lowercase, human-readable identifier that will appear
    in logs, warnings, and the readiness report.
    """
    FONTS = "fonts"
    IMAGES = "images"
    VIDEOS = "videos"
    SKELETONS = "skeletons"
    DOM_STABILITY = "dom_stability"
    LAYOUT_STABILITY = "layout_stability"
    SCROLL_DISCOVERY = "scroll_discovery"


class CheckCriticality(str, Enum):
    """
    Whether a check failure should abort the scan or just warn.

    CRITICAL:     Failure means the scan cannot produce useful output.
                  Examples: browser crash, navigation failure, DNS error.
                  These are handled at the BrowserService level (before the
                  readiness engine even runs), so they don't appear as
                  CheckCategory values.

    NON_CRITICAL: Failure degrades scan quality but a useful screenshot
                  and analysis can still be produced. All readiness checks
                  in the pipeline are non-critical — they improve quality
                  but should never block the scan.
    """
    CRITICAL = "critical"
    NON_CRITICAL = "non_critical"


# ---------------------------------------------------------------------------
# Per-check result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CheckResult:
    """
    The outcome of a single readiness check.

    This is the atomic unit of the readiness report. Each check in the
    pipeline produces exactly one CheckResult, regardless of whether it
    passed, timed out, or was skipped.

    Attributes:
        name:         Which check this result is for (e.g., FONTS, IMAGES).
        criticality:  Whether failure should abort or just warn.
        passed:       True if the check completed successfully.
        elapsed_ms:   Wall-clock time this check consumed, in milliseconds.
        message:      Human-readable description of what happened.
                      For passed checks: "All 12 images loaded"
                      For failed checks: "Image loading timed out after 10000ms — 3 of 12 images still loading"
                      For skipped checks: "Skipped — global time budget exhausted"
    """
    name: CheckCategory
    criticality: CheckCriticality
    passed: bool
    elapsed_ms: float
    message: str


# ---------------------------------------------------------------------------
# Aggregated pipeline result
# ---------------------------------------------------------------------------

# Weights for scan quality score computation.
# Higher weight = more impact on the final score.
#
# Why these weights:
# - DOM_STABILITY and LAYOUT_STABILITY are the strongest signals that the
#   page is visually settled. A screenshot taken during layout shifts is
#   unreliable, so these carry the highest weight.
# - IMAGES matter because broken/missing images are immediately visible
#   in screenshots and produce misleading analysis.
# - SKELETONS are the #1 visual issue in SPAs — gray placeholder
#   rectangles instead of real content.
# - FONTS affect text rendering (FOIT/FOUT) but the impact is less
#   dramatic than missing content.
# - VIDEOS are niche — most pages have zero videos, so this check
#   rarely affects overall quality.
# - SCROLL_DISCOVERY improves completeness for long pages but isn't
#   strictly about visual fidelity of what's already visible.

CHECK_WEIGHTS: dict[CheckCategory, float] = {
    CheckCategory.FONTS: 0.10,
    CheckCategory.IMAGES: 0.20,
    CheckCategory.VIDEOS: 0.05,
    CheckCategory.SKELETONS: 0.15,
    CheckCategory.DOM_STABILITY: 0.20,
    CheckCategory.LAYOUT_STABILITY: 0.20,
    CheckCategory.SCROLL_DISCOVERY: 0.10,
}


def compute_scan_quality_score(checks: tuple[CheckResult, ...]) -> float:
    """
    Compute a weighted quality score from a set of check results.

    Returns a float between 0.0 and 1.0 representing confidence in the
    scan's visual fidelity.

    Scoring algorithm:
    1. Only non-critical checks contribute to the score (critical checks
       are pass/fail gates — if one fails, the scan is aborted entirely).
    2. Each check has a predefined weight (see CHECK_WEIGHTS).
    3. Passed checks contribute their full weight. Failed checks contribute
       zero.
    4. The raw score is normalised by the sum of weights of checks that
       were actually executed (not the theoretical maximum). This means
       if a check was disabled in config (e.g., wait_for_videos=False),
       it doesn't penalise the score.

    Example:
        fonts=✓, images=✓, videos=✗, skeletons=✓, dom=✓, layout=✗
        earned  = 0.10 + 0.20 + 0.00 + 0.15 + 0.20 + 0.00 = 0.65
        possible = 0.10 + 0.20 + 0.05 + 0.15 + 0.20 + 0.20 = 0.90
        score = 0.65 / 0.90 ≈ 0.722
    """
    earned = 0.0
    possible = 0.0

    for check in checks:
        if check.criticality != CheckCriticality.NON_CRITICAL:
            continue

        weight = CHECK_WEIGHTS.get(check.name, 0.0)
        possible += weight
        if check.passed:
            earned += weight

    if possible == 0.0:
        # No non-critical checks ran (all disabled or skipped).
        # Default to 1.0 — we have no evidence of poor quality.
        return 1.0

    return round(earned / possible, 3)


@dataclass(frozen=True)
class ReadinessResult:
    """
    The complete output of the Page Readiness Engine pipeline.

    This is the primary return type of PageReadinessEngine.wait_until_ready().
    It replaces the previous None return, giving callers full visibility into
    what the engine did and how confident the result is.

    Attributes:
        checks:               All check results, in pipeline execution order.
        total_elapsed_seconds: Wall-clock time for the entire pipeline.
        scan_quality_score:    0.0–1.0 confidence score (see compute_scan_quality_score).
        warnings:             Human-readable messages for checks that timed out
                              or degraded. Empty tuple if everything passed.
        has_critical_failure: True if any critical check failed. When True,
                              the scan should be aborted (no screenshot/analysis).
                              In practice, critical failures (navigation, DNS)
                              are handled before the readiness engine runs,
                              so this will almost always be False.
    """
    checks: tuple[CheckResult, ...]
    total_elapsed_seconds: float
    scan_quality_score: float
    warnings: tuple[str, ...]
    has_critical_failure: bool

    @property
    def completed_checks(self) -> tuple[CheckResult, ...]:
        """Checks that passed successfully."""
        return tuple(c for c in self.checks if c.passed)

    @property
    def failed_checks(self) -> tuple[CheckResult, ...]:
        """Checks that timed out or failed."""
        return tuple(c for c in self.checks if not c.passed)
