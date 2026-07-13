"""
Artifact Service
================

The single point of contact between the application and the filesystem
for all scan-related persistence.

This service owns the entire artifact directory tree:

    artifacts/
        scan_<id>/
            report.json            ← master report (canonical scan record)
            analysis/
                metadata.json      ← individual analysis modules
                readiness.json
                console.json
                network.json
                assets.json
                forms.json
                links.json
                dom.json
            media/
                screenshot.png     ← full-page screenshot
            logs/
                scan.log           ← lifecycle log (JSON lines)
        comparisons/
            comp_<id>/
                report.json        ← structured regression report
                diff.png           ← composite diff image

Design principles:
    - NO other service or endpoint performs filesystem I/O for scan data.
    - BrowserService returns bytes/dicts in memory; ArtifactService writes them.
    - All paths are derived from scan_id — no path construction outside this file.
    - Writes are atomic where possible (write to temp, rename).
    - All JSON is human-readable (indent=2, ensure_ascii=False).

Future extensibility:
    The directory structure supports additional outputs (AI reports, HAR files,
    trace files, videos) by simply adding new subdirectories or files. No
    existing code needs to change.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ArtifactService:
    """
    Manages creation, storage, and retrieval of scan artifact bundles.

    Each scan gets its own directory under the artifacts root. This service
    handles the full lifecycle: creating the directory tree, writing every
    file type, and reading them back for the API.

    Args:
        artifacts_dir: Root directory for all scan artifacts.
                       Defaults to "artifacts" (relative to the backend
                       working directory). Created automatically if missing.
    """

    def __init__(self, artifacts_dir: str = "artifacts") -> None:
        self._root = Path(artifacts_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Path helpers (private)
    # ------------------------------------------------------------------

    def _scan_dir(self, scan_id: str) -> Path:
        """Root directory for a single scan's artifacts."""
        return self._root / scan_id

    def _analysis_dir(self, scan_id: str) -> Path:
        return self._scan_dir(scan_id) / "analysis"

    def _media_dir(self, scan_id: str) -> Path:
        return self._scan_dir(scan_id) / "media"

    def _logs_dir(self, scan_id: str) -> Path:
        return self._scan_dir(scan_id) / "logs"

    def _comparison_dir(self, comparison_id: str) -> Path:
        """Root directory for a single visual comparison."""
        return self._root / "comparisons" / comparison_id

    # ------------------------------------------------------------------
    # Directory creation
    # ------------------------------------------------------------------

    def create_scan_directory(self, scan_id: str) -> Path:
        """
        Create the full directory tree for a scan.

        Creates:
            artifacts/<scan_id>/
            artifacts/<scan_id>/analysis/
            artifacts/<scan_id>/media/
            artifacts/<scan_id>/logs/

        Returns:
            Path to the scan's root directory.

        Raises:
            OSError: If directory creation fails (permissions, disk full, etc.).
        """
        scan_dir = self._scan_dir(scan_id)

        # Create all subdirectories in one pass
        for subdir in (self._analysis_dir(scan_id),
                       self._media_dir(scan_id),
                       self._logs_dir(scan_id)):
            subdir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Created artifact directory: {scan_dir}")
        return scan_dir

    def create_comparison_directory(self, comparison_id: str) -> Path:
        """
        Create the directory for a visual comparison.

        Creates: artifacts/comparisons/<comparison_id>/
        """
        comp_dir = self._comparison_dir(comparison_id)
        comp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created comparison directory: {comp_dir}")
        return comp_dir

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def _write_json(self, path: Path, data: Any) -> None:
        """
        Write data to a JSON file with consistent formatting.

        All JSON files use:
        - indent=2 for human readability
        - ensure_ascii=False for proper unicode support
        - UTF-8 encoding

        Args:
            path: Absolute path to the output file.
            data: Any JSON-serialisable Python object.
        """
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        logger.debug(f"Wrote JSON artifact: {path}")

    def save_screenshot(self, scan_id: str, screenshot_bytes: bytes) -> Path:
        """
        Save a screenshot PNG to the scan's media directory.

        Args:
            scan_id: The scan identifier.
            screenshot_bytes: Raw PNG bytes from Playwright's page.screenshot().

        Returns:
            Path to the saved screenshot file.
        """
        screenshot_path = self._media_dir(scan_id) / "screenshot.png"
        screenshot_path.write_bytes(screenshot_bytes)
        logger.info(f"Saved screenshot: {screenshot_path}")
        return screenshot_path

    def save_analysis_artifacts(
        self,
        scan_id: str,
        analysis_data: dict[str, Any],
        readiness_data: dict[str, Any] | None = None,
    ) -> None:
        """
        Save individual analysis category files.

        Each top-level key in analysis_data becomes its own JSON file:
            analysis_data["metadata"] → analysis/metadata.json
            analysis_data["console"]  → analysis/console.json
            etc.

        Readiness data is saved separately as analysis/readiness.json
        because it comes from a different engine (PageReadinessEngine)
        than the analysis categories (AnalysisService).

        This granular storage allows future AI modules to load only
        the categories they need instead of parsing the entire report.

        Args:
            scan_id: The scan identifier.
            analysis_data: Dict with keys matching analysis categories.
            readiness_data: Optional readiness report dict.
        """
        analysis_dir = self._analysis_dir(scan_id)

        # Map analysis keys to filenames
        # The analysis response has keys like "metadata", "headings", "images", etc.
        # We write each as its own file for granular access.
        for key, value in analysis_data.items():
            filename = f"{key}.json"
            self._write_json(analysis_dir / filename, value)

        if readiness_data is not None:
            self._write_json(analysis_dir / "readiness.json", readiness_data)

        logger.info(f"Saved {len(analysis_data)} analysis artifacts for {scan_id}")

    def save_report(self, scan_id: str, report: dict[str, Any]) -> Path:
        """
        Save the master report.json for a scan.

        The master report is the canonical representation of a completed scan.
        It contains everything: scan metadata, full analysis, readiness,
        version info. This is what GET /api/v1/scans/{scan_id} returns.

        Args:
            scan_id: The scan identifier.
            report: The complete report as a serialisable dict.

        Returns:
            Path to the saved report file.
        """
        report_path = self._scan_dir(scan_id) / "report.json"
        self._write_json(report_path, report)
        logger.info(f"Saved master report: {report_path}")
        return report_path

    def save_scan_log(self, scan_id: str, log_entries: list[dict[str, str]]) -> Path:
        """
        Save the scan lifecycle log.

        Written as a JSON array of {timestamp, message} objects.
        This is a debug artifact for investigating failed scans.

        Args:
            scan_id: The scan identifier.
            log_entries: List of log entry dicts from ScanLogCollector.

        Returns:
            Path to the saved log file.
        """
        log_path = self._logs_dir(scan_id) / "scan.log"
        self._write_json(log_path, log_entries)
        logger.info(f"Saved scan log: {log_path} ({len(log_entries)} entries)")
        return log_path

    def save_diff_image(self, comparison_id: str, diff_bytes: bytes) -> Path:
        """Save a generated diff image to the comparison directory."""
        diff_path = self._comparison_dir(comparison_id) / "diff.png"
        diff_path.write_bytes(diff_bytes)
        logger.info(f"Saved diff image: {diff_path}")
        return diff_path

    def save_comparison_report(self, comparison_id: str, report: dict[str, Any]) -> Path:
        """Save the master report for a visual comparison."""
        report_path = self._comparison_dir(comparison_id) / "report.json"
        self._write_json(report_path, report)
        logger.info(f"Saved comparison report: {report_path}")
        return report_path

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_scan_report(self, scan_id: str) -> dict[str, Any] | None:
        """
        Load and return the master report for a scan.

        Returns None if the scan directory or report file doesn't exist.
        This is intentional — the caller (API endpoint) converts None
        to a 404 response.

        Args:
            scan_id: The scan identifier.

        Returns:
            The report as a dict, or None if not found.
        """
        report_path = self._scan_dir(scan_id) / "report.json"
        if not report_path.exists():
            return None

        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_screenshot_path(self, scan_id: str) -> Path | None:
        """
        Return the absolute path to a scan's screenshot.

        Returns None if the file doesn't exist. The API endpoint
        uses this path with FileResponse to serve the image.

        Args:
            scan_id: The scan identifier.

        Returns:
            Absolute Path to the screenshot, or None if not found.
        """
        screenshot_path = self._media_dir(scan_id) / "screenshot.png"
        if not screenshot_path.exists():
            return None
        return screenshot_path

    def scan_exists(self, scan_id: str) -> bool:
        """Check whether a scan directory exists."""
        return self._scan_dir(scan_id).is_dir()

    def list_scans(self) -> list[dict[str, Any]]:
        """
        List all available scans with summary information.

        Reads each scan's report.json to extract summary fields.
        Returns results sorted by creation time (most recent first).

        Scans without a report.json (e.g., failed before report generation)
        are included with minimal metadata derived from the directory name.

        Returns:
            List of scan summary dicts, each containing:
            scan_id, url, status, created_at, duration_seconds.
        """
        scans: list[dict[str, Any]] = []

        if not self._root.exists():
            return scans

        for scan_dir in sorted(self._root.iterdir(), reverse=True):
            if not scan_dir.is_dir():
                continue

            scan_id = scan_dir.name
            report_path = scan_dir / "report.json"

            if report_path.exists():
                try:
                    with open(report_path, "r", encoding="utf-8") as f:
                        report = json.load(f)

                    scan_info = report.get("scan_info", {})
                    scans.append({
                        "scan_id": scan_info.get("scan_id", scan_id),
                        "url": scan_info.get("url", "unknown"),
                        "status": scan_info.get("status", "unknown"),
                        "created_at": scan_info.get("started_at"),
                        "duration_seconds": scan_info.get("duration_seconds"),
                    })
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning(f"Failed to read report for {scan_id}: {exc}")
                    scans.append({
                        "scan_id": scan_id,
                        "url": "unknown",
                        "status": "corrupted",
                        "created_at": None,
                        "duration_seconds": None,
                    })
            else:
                # Scan directory exists but no report — likely a failed scan
                scans.append({
                    "scan_id": scan_id,
                    "url": "unknown",
                    "status": "incomplete",
                    "created_at": None,
                    "duration_seconds": None,
                })

        return scans
