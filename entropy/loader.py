"""Data loader for JSON and CSV files."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LoadResult:
    """Result of loading a data file."""
    data: list[dict]
    original_size_bytes: int
    source_path: str
    format: str


def load(file_path: str) -> LoadResult:
    """Load data from a JSON or CSV file.

    Args:
        file_path: Path to a .json or .csv file.

    Returns:
        LoadResult containing the parsed data and original serialized size.

    Raises:
        ValueError: If the file extension is not .json or .csv.
        FileNotFoundError: If the file does not exist.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    raw_bytes = path.read_bytes()
    original_size = len(raw_bytes)
    suffix = path.suffix.lower()

    if suffix == ".json":
        data = _load_json(raw_bytes)
        fmt = "json"
    elif suffix == ".csv":
        data = _load_csv(raw_bytes)
        fmt = "csv"
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use .json or .csv.")

    return LoadResult(
        data=data,
        original_size_bytes=original_size,
        source_path=str(path.resolve()),
        format=fmt,
    )


def _load_json(raw: bytes) -> list[dict]:
    """Parse JSON bytes into a list of dicts."""
    parsed = json.loads(raw.decode("utf-8"))

    if isinstance(parsed, list):
        return [row for row in parsed if isinstance(row, dict)]
    if isinstance(parsed, dict):
        return [parsed]

    raise ValueError("JSON root must be an array of objects or a single object.")


def _load_csv(raw: bytes) -> list[dict]:
    """Parse CSV bytes into a list of dicts using DictReader."""
    text = raw.decode("utf-8")
    reader = csv.DictReader(text.splitlines())
    return [dict(row) for row in reader]
