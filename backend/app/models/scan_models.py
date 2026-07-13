"""
Scan Domain Models
==================

Core identity and lifecycle types for the scan system.

These are domain models — they define what a scan IS, not how it's
serialised (schemas) or how it's stored (services). They sit at the
foundation of the artifact system: every service, endpoint, and schema
in this milestone depends on ScanStatus and generate_scan_id().

Why models/ and not schemas/?
    schemas/ is for Pydantic models at the API boundary (JSON in/out).
    models/ is for internal domain types that multiple layers share.
    ScanStatus and scan IDs are used by services, endpoints, and schemas
    alike — they belong in the domain layer.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum


class ScanStatus(str, Enum):
    """
    Lifecycle state of a scan execution.

    Inherits from str so the enum serialises to a plain lowercase string
    in JSON (e.g., "completed" instead of "ScanStatus.COMPLETED").

    Although scans currently execute synchronously (the endpoint blocks
    until completion), implementing the full lifecycle now means:
    - Future background workers can set PENDING → RUNNING → COMPLETED
      without changing the model.
    - Failed scans are recorded with FAILED status instead of being lost.

    State transitions:
        PENDING → RUNNING → COMPLETED
                         ↘ FAILED
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def generate_scan_id() -> str:
    """
    Generate a unique scan identifier.

    Format: scan_YYYYMMDD_HHMMSS_<4-char-hex>

    Examples:
        scan_20260713_143055_a81c
        scan_20260713_143055_f3e2

    Design rationale:
    - Timestamp prefix: human-readable and chronologically sortable
      when browsing the artifacts/ directory in a file explorer.
    - 4-char hex suffix: derived from uuid4, provides uniqueness
      within the same second. 65,536 possible values per second
      is far more than enough for a synchronous scanner.
    - 'scan_' prefix: makes the ID self-describing in logs, APIs,
      and directory listings.

    Returns:
        A unique scan ID string.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_hex = uuid.uuid4().hex[:4]
    return f"scan_{timestamp}_{short_hex}"
