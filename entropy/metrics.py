"""Metrics tracking for entropy reduction stages."""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class StageResult:
    """Result metrics for a single pipeline stage."""
    stage_name: str
    input_size: int
    output_size: int
    reduction_pct: float


def compute_size(data: list[dict] | bytes) -> int:
    """Return the size in bytes of data.

    If data is a list of dicts, it is JSON-serialized first.
    If data is already bytes, its length is returned directly.

    Args:
        data: Data to measure.

    Returns:
        Size in bytes.
    """
    if isinstance(data, bytes):
        return len(data)
    return len(json.dumps(data, default=str).encode("utf-8"))


def format_size(size_bytes: int) -> str:
    """Format a byte count as a human-readable string.

    Args:
        size_bytes: Number of bytes.

    Returns:
        Formatted string like '1.23 KB' or '456 B'.
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
