"""
Scan Log Collector
==================

Captures timestamped lifecycle events for a single scan execution.

This is NOT a Python logging.Handler. It's a structured data collector
that accumulates scan-specific events in memory, then returns them as
a list for ArtifactService to persist as logs/scan.log.

Why not use Python's logging module?
    1. Python logging is for application-level routing (stdout, files,
       monitoring). Scan logs are data artifacts — they belong inside
       each scan's directory, not in a shared log file.
    2. Attaching per-request file handlers to the logging system is
       fragile and creates concurrency issues.
    3. Scan log entries are structured (timestamp + message), not
       free-form text. Keeping them as data lets us serialize to
       any format (JSON, text, etc.).

Usage:
    log = ScanLogCollector()
    log.add("Scan started")
    log.add("Browser launched")
    ...
    entries = log.entries  # List of ScanLogEntry
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ScanLogEntry:
    """
    A single timestamped log entry from a scan execution.

    Attributes:
        timestamp: ISO 8601 formatted timestamp of when the event occurred.
        message:   Human-readable description of the lifecycle event.
    """
    timestamp: str
    message: str


class ScanLogCollector:
    """
    Collects scan lifecycle events in memory during a scan execution.

    Create one instance per scan. Call add() at each major lifecycle point.
    After the scan completes (or fails), read .entries to get the full log.

    Thread safety: Not thread-safe. Designed for synchronous, single-scan use.
    This matches the current BrowserService design where each scan runs on
    a single thread.
    """

    def __init__(self) -> None:
        self._entries: list[ScanLogEntry] = []

    def add(self, message: str) -> None:
        """
        Record a timestamped lifecycle event.

        Args:
            message: Human-readable description of the event.
                     Examples: "Scan started", "Browser launched",
                     "Navigation completed", "Analysis failed: timeout".
        """
        entry = ScanLogEntry(
            timestamp=datetime.now().isoformat(),
            message=message,
        )
        self._entries.append(entry)

    @property
    def entries(self) -> list[ScanLogEntry]:
        """Return all collected log entries in chronological order."""
        return list(self._entries)

    def to_serializable(self) -> list[dict[str, str]]:
        """
        Return entries as plain dicts for JSON serialisation.

        ArtifactService calls this when writing logs/scan.log.
        Returning dicts (not dataclasses) keeps the serialisation
        concern out of the dataclass itself.
        """
        return [
            {"timestamp": e.timestamp, "message": e.message}
            for e in self._entries
        ]
