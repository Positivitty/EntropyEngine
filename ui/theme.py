"""Entropy Engine - Theme constants and visual configuration."""

# ── Color Palette ──────────────────────────────────────────────────────────
COLORS = {
    "primary": "#00ff41",   # Neon green - main text
    "accent": "#00d4ff",    # Cyan - highlights and emphasis
    "warning": "#ffd700",   # Yellow - warnings and deltas
    "dim": "#555555",       # Gray - secondary / muted text
    "bg": "#000000",        # Black - implied background
}

# ── Pipeline Stage Display Names ───────────────────────────────────────────
STAGE_NAMES = {
    "dedup": "DEDUPLICATION",
    "encode": "DICT ENCODING",
    "trim": "FIELD TRIMMING",
    "compress": "COMPRESSION",
}

# ── Boot Sequence Messages ─────────────────────────────────────────────────
BOOT_MESSAGES = [
    "INITIALIZING ENTROPY ENGINE...",
    "LOADING CORE MODULES...",
    "CALIBRATING OPTIMIZATION MATRIX...",
    "SCANNING ENTROPY VECTORS...",
    "LOCKING COMPRESSION PIPELINE...",
    "SYSTEM READY.",
]
