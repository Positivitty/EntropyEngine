"""Entropy Engine - ASCII animation helpers and visual components."""

from __future__ import annotations

from ui.theme import COLORS, STAGE_NAMES


# Pipeline stage keys in processing order
_PIPELINE_STAGES = ["dedup", "encode", "trim", "compress"]

_PIPELINE_LABELS = {
    "raw": "INPUT",
    "dedup": "DEDUP",
    "encode": "ENCODE",
    "trim": "TRIM",
    "compress": "COMPRESS",
}


def pipeline_diagram(active_stage: str | None = None) -> str:
    """Return a compact ASCII pipeline diagram with active-stage highlighting."""
    arrow = f"[{COLORS['dim']}]>>[/{COLORS['dim']}]"

    def _node(key: str, label: str) -> str:
        if key == active_stage:
            return f"[bold {COLORS['primary']}][{label}][/bold {COLORS['primary']}]"
        return f"[{COLORS['dim']}][{label}][/{COLORS['dim']}]"

    parts = [_node("raw", _PIPELINE_LABELS["raw"])]
    for stage in _PIPELINE_STAGES:
        parts.append(arrow)
        parts.append(_node(stage, _PIPELINE_LABELS[stage]))

    return " ".join(parts)


def progress_bar(pct: float, width: int = 30) -> str:
    """Return a fixed-width progress bar string.

    Example: [████████████░░░░░░░░░░░░░░░░░░] 40%
    """
    pct = max(0.0, min(100.0, pct))
    filled = int(round(width * pct / 100))
    empty = width - filled
    bar = "\u2588" * filled + "\u2591" * empty
    return f"[{bar}] {pct:>3.0f}%"


def stage_header(name: str) -> str:
    """Return a bordered stage header line.

    Example:
        ┌─── DEDUPLICATION ─────────────────────┐
    """
    display = STAGE_NAMES.get(name, name.upper())
    label = f"\u2500\u2500\u2500 {display} "
    padding = max(0, 40 - len(label) - 2)
    line = "\u2500" * padding
    return f"\u250c{label}{line}\u2510"


def size_comparison(before: float, after: float) -> str:
    """Return a formatted size-reduction string.

    Example: 2.1 KB -> 1.6 KB  [-23.8%]
    """
    def _fmt(b: float) -> str:
        if b >= 1_048_576:
            return f"{b / 1_048_576:.1f} MB"
        if b >= 1024:
            return f"{b / 1024:.1f} KB"
        return f"{b:.0f} B"

    delta = ((after - before) / before * 100) if before else 0.0
    return f"{_fmt(before)} \u2192 {_fmt(after)}  [{delta:+.1f}%]"
