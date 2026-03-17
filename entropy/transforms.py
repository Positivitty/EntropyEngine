"""Data transformation functions for entropy reduction."""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass, field


def deduplicate(data: list[dict]) -> list[dict]:
    """Remove exact duplicate rows.

    Two rows are considered duplicates if their JSON serializations match
    (with sorted keys for consistency).

    Args:
        data: List of dicts to deduplicate.

    Returns:
        New list with duplicates removed, preserving original order.
    """
    seen: set[str] = set()
    result: list[dict] = []

    for row in data:
        key = json.dumps(row, sort_keys=True, default=str)
        if key not in seen:
            seen.add(key)
            result.append(row)

    return result


@dataclass
class DictionaryEncodeResult:
    """Result of dictionary encoding."""
    encoded_data: list[dict]
    dictionary: dict[str, dict[int, str]]
    code_maps: dict[str, dict[str, int]] = field(repr=False)


def dictionary_encode(data: list[dict]) -> DictionaryEncodeResult:
    """Replace repeated string values with integer codes.

    For each field, if a string value appears more than once across all rows,
    it gets assigned an integer code. Fields with all-unique values are left
    unchanged.

    Args:
        data: List of dicts to encode.

    Returns:
        DictionaryEncodeResult with encoded data, the reverse dictionary
        (code -> original value per field), and the forward code maps.
    """
    if not data:
        return DictionaryEncodeResult(
            encoded_data=[], dictionary={}, code_maps={}
        )

    # Count string value frequencies per field
    field_values: dict[str, dict[str, int]] = {}
    for row in data:
        for key, value in row.items():
            if isinstance(value, str):
                field_values.setdefault(key, {})
                field_values[key][value] = field_values[key].get(value, 0) + 1

    # Build code maps only for fields that have repeated values
    code_maps: dict[str, dict[str, int]] = {}
    reverse_dict: dict[str, dict[int, str]] = {}

    for field_name, value_counts in field_values.items():
        repeated = {v for v, count in value_counts.items() if count > 1}
        if not repeated:
            continue

        codes: dict[str, int] = {}
        reverse: dict[int, str] = {}
        next_code = 0

        for value in sorted(value_counts.keys()):
            if value in repeated:
                codes[value] = next_code
                reverse[next_code] = value
                next_code += 1

        code_maps[field_name] = codes
        reverse_dict[field_name] = reverse

    # Encode the data
    encoded: list[dict] = []
    for row in data:
        new_row = dict(row)
        for field_name, codes in code_maps.items():
            if field_name in new_row and new_row[field_name] in codes:
                new_row[field_name] = codes[new_row[field_name]]
        encoded.append(new_row)

    return DictionaryEncodeResult(
        encoded_data=encoded,
        dictionary=reverse_dict,
        code_maps=code_maps,
    )


def field_trim(data: list[dict]) -> list[dict]:
    """Strip whitespace from string values and remove null/empty fields.

    Args:
        data: List of dicts to trim.

    Returns:
        New list of dicts with trimmed strings and no null/empty fields.
    """
    result: list[dict] = []

    for row in data:
        new_row: dict = {}
        for key, value in row.items():
            if value is None:
                continue
            if isinstance(value, str):
                stripped = value.strip()
                if stripped == "":
                    continue
                new_row[key] = stripped
            else:
                new_row[key] = value
        result.append(new_row)

    return result


def compress(data: list[dict]) -> bytes:
    """Serialize data to JSON and gzip compress it.

    Args:
        data: List of dicts to compress.

    Returns:
        Gzip-compressed bytes of the JSON serialization.
    """
    serialized = json.dumps(data, separators=(",", ":"), default=str)
    return gzip.compress(serialized.encode("utf-8"))
