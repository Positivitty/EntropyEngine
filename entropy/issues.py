from __future__ import annotations

import gzip
import json
import math
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class FieldDetail:
    """Detail about a specific field's contribution to an issue."""
    field_name: str
    unique_values: int
    total_values: int
    repetition_ratio: float  # 0-1, higher = more repetition
    space_contribution: int  # bytes this field contributes
    top_values: list[tuple[str, int]]  # (value, count) top 5


@dataclass
class Issue:
    """A detected inefficiency in the dataset."""
    id: str                    # e.g. "duplicate_records", "string_repetition", "excess_whitespace", "compression_opportunity"
    title: str                 # Human readable title
    severity: str              # "high", "medium", "low"
    impact_pct: float          # % of total size this issue contributes
    impact_bytes: int          # absolute bytes wasted
    description: str           # 1-2 sentence description
    explanation: str           # Deep engineer-level explanation
    affected_fields: list[FieldDetail]  # field-level breakdown
    fix_stage: str             # which pipeline stage fixes this: "dedup", "encode", "trim", "compress"
    projected_1m: dict         # {"wasted_mb": float, "savings_mb": float} projected to 1M records


@dataclass
class IssueReport:
    """Complete analysis report for a dataset."""
    total_size: int
    record_count: int
    field_count: int
    issues: list[Issue]
    primary_issue: Issue | None  # the highest impact issue
    efficiency_score: int        # 0-100, where 100 = perfectly efficient


def _project_to_1m(wasted_bytes: int, record_count: int) -> dict:
    """Project waste to 1M records."""
    if record_count == 0:
        return {"wasted_mb": 0.0, "savings_mb": 0.0}
    per_record = wasted_bytes / record_count
    at_1m = per_record * 1_000_000
    mb = at_1m / 1_048_576
    return {"wasted_mb": round(mb, 2), "savings_mb": round(mb, 2)}


def _detect_duplicates(
    data: list[dict], total_size: int, record_count: int
) -> Issue | None:
    """Detect exact duplicate records by hashing each row."""
    if record_count == 0:
        return None

    row_hashes: list[str] = []
    for row in data:
        row_hashes.append(json.dumps(row, sort_keys=True, default=str))

    counts = Counter(row_hashes)
    duplicate_count = sum(c - 1 for c in counts.values() if c > 1)

    if duplicate_count == 0:
        return None

    avg_row_size = total_size / record_count
    wasted_bytes = int(duplicate_count * avg_row_size)
    impact_pct = round(wasted_bytes / total_size * 100, 2)

    if impact_pct > 20:
        severity = "high"
    elif impact_pct > 5:
        severity = "medium"
    else:
        severity = "low"

    unique_count = len(counts)

    return Issue(
        id="duplicate_records",
        title=f"{duplicate_count} exact duplicate records detected",
        severity=severity,
        impact_pct=impact_pct,
        impact_bytes=wasted_bytes,
        description=(
            f"{duplicate_count} of {record_count} records are exact duplicates, "
            f"wasting {wasted_bytes:,} bytes ({impact_pct}% of total size)."
        ),
        explanation=(
            "Exact duplicates typically originate from ETL pipelines that lack "
            "idempotency guards, merge operations that join on non-unique keys, "
            "or retry logic in producers that re-emit records after transient "
            "failures. Each duplicate consumes storage linearly -- doubling "
            "duplicates doubles waste. While columnar formats and gzip can "
            "collapse duplicate byte sequences, the redundant rows still inflate "
            "scan width during query execution, increasing both I/O and CPU cost. "
            "Deduplication should happen as early as possible in the pipeline to "
            "avoid propagating waste downstream into aggregations and indexes."
        ),
        affected_fields=[],
        fix_stage="dedup",
        projected_1m=_project_to_1m(wasted_bytes, record_count),
    )


def _detect_repetition(
    data: list[dict], total_size: int, record_count: int
) -> Issue | None:
    """Detect high string repetition across fields."""
    if record_count == 0:
        return None

    field_details: list[FieldDetail] = []

    all_keys: set[str] = set()
    for row in data:
        all_keys.update(row.keys())

    for key in sorted(all_keys):
        values = [row.get(key) for row in data if key in row]
        string_values = [str(v) for v in values if v is not None and isinstance(v, str)]

        if not string_values:
            continue

        total_values = len(string_values)
        counter = Counter(string_values)
        unique_values = len(counter)
        repetition_ratio = round(1 - (unique_values / total_values), 4) if total_values > 0 else 0.0

        if repetition_ratio <= 0.3:
            continue

        # Calculate space wasted: actual string bytes minus what integer codes would cost
        actual_bytes = sum(len(v.encode()) for v in string_values)
        # With dictionary encoding: store each unique value once + an integer code per row
        dict_bytes = sum(len(v.encode()) for v in counter.keys())
        # Integer codes: ceil(log2(unique_values)) bits per code, at least 1 byte
        code_size = max(1, math.ceil(math.log2(max(unique_values, 2)) / 8))
        dict_bytes += code_size * total_values
        space_contribution = max(0, actual_bytes - dict_bytes)

        top_values = counter.most_common(5)

        field_details.append(FieldDetail(
            field_name=key,
            unique_values=unique_values,
            total_values=total_values,
            repetition_ratio=repetition_ratio,
            space_contribution=space_contribution,
            top_values=top_values,
        ))

    if not field_details:
        return None

    field_details.sort(key=lambda fd: fd.space_contribution, reverse=True)

    total_wasted = sum(fd.space_contribution for fd in field_details)
    impact_pct = round(total_wasted / total_size * 100, 2) if total_size > 0 else 0.0

    worst_field = field_details[0]

    if impact_pct > 15:
        severity = "high"
    elif impact_pct > 5:
        severity = "medium"
    else:
        severity = "low"

    high_rep_count = sum(1 for fd in field_details if fd.repetition_ratio > 0.5)

    return Issue(
        id="string_repetition",
        title=f"High string repetition in '{worst_field.field_name}' ({worst_field.repetition_ratio:.0%} repeated)",
        severity=severity,
        impact_pct=impact_pct,
        impact_bytes=total_wasted,
        description=(
            f"{len(field_details)} field(s) contain highly repetitive string values. "
            f"'{worst_field.field_name}' has {worst_field.unique_values} unique values "
            f"across {worst_field.total_values} rows ({worst_field.repetition_ratio:.0%} repetition)."
        ),
        explanation=(
            "In row-oriented formats like JSON and CSV, each string value is stored "
            "independently with no shared references -- writing the same 20-byte "
            "status string 10,000 times costs 200 KB regardless of cardinality. "
            "Dictionary encoding replaces each occurrence with a compact integer code "
            "and stores each unique string exactly once in a lookup table, reducing "
            "storage to O(unique) for the strings plus O(N) small integers. This is "
            "the same technique Parquet and ORC use for low-cardinality columns. The "
            "savings compound during serialization and network transfer since fewer "
            "distinct byte sequences means higher compressor locality."
        ),
        affected_fields=field_details,
        fix_stage="encode",
        projected_1m=_project_to_1m(total_wasted, record_count),
    )


def _detect_whitespace(
    data: list[dict], total_size: int, record_count: int
) -> Issue | None:
    """Detect excess leading/trailing whitespace and empty values in string fields."""
    if record_count == 0:
        return None

    all_keys: set[str] = set()
    for row in data:
        all_keys.update(row.keys())

    field_details: list[FieldDetail] = []
    total_ws_bytes = 0

    for key in sorted(all_keys):
        ws_bytes_field = 0
        ws_count = 0
        empty_count = 0
        total_values = 0
        value_counter: Counter = Counter()

        for row in data:
            if key not in row:
                continue
            val = row[key]
            if not isinstance(val, str):
                continue

            total_values += 1

            if val == "" or val is None:
                empty_count += 1
                continue

            stripped = val.strip()
            diff = len(val.encode()) - len(stripped.encode())
            if diff > 0:
                ws_bytes_field += diff
                ws_count += 1
                value_counter[repr(val)] += 1

        if ws_count == 0 and empty_count == 0:
            continue

        total_ws_bytes += ws_bytes_field
        ratio = round(ws_count / total_values, 4) if total_values > 0 else 0.0

        field_details.append(FieldDetail(
            field_name=key,
            unique_values=ws_count + empty_count,
            total_values=total_values,
            repetition_ratio=ratio,
            space_contribution=ws_bytes_field,
            top_values=value_counter.most_common(5),
        ))

    if total_ws_bytes == 0 and not field_details:
        return None

    field_details.sort(key=lambda fd: fd.space_contribution, reverse=True)

    impact_pct = round(total_ws_bytes / total_size * 100, 2) if total_size > 0 else 0.0

    if impact_pct > 10:
        severity = "high"
    elif impact_pct > 2:
        severity = "medium"
    else:
        severity = "low"

    affected_count = len(field_details)

    return Issue(
        id="excess_whitespace",
        title=f"Excess whitespace detected across {affected_count} field(s)",
        severity=severity,
        impact_pct=impact_pct,
        impact_bytes=total_ws_bytes,
        description=(
            f"{affected_count} field(s) contain leading or trailing whitespace, "
            f"totaling {total_ws_bytes:,} wasted bytes ({impact_pct}% of dataset)."
        ),
        explanation=(
            "Stray whitespace typically accumulates from CSV parsers that preserve "
            "padding, copy-paste from formatted documents, or user input fields that "
            "lack client-side trimming. Beyond the raw storage cost, untrimmed strings "
            "cause subtle correctness bugs: 'Active' != ' Active' in equality checks "
            "and GROUP BY clauses, leading to phantom categories in aggregations. "
            "Whitespace also disrupts lexicographic sort order, pushing padded values "
            "to unexpected positions. Trimming should be applied at ingestion time "
            "before any downstream indexing or deduplication."
        ),
        affected_fields=field_details,
        fix_stage="trim",
        projected_1m=_project_to_1m(total_ws_bytes, record_count),
    )


def _detect_compression_opportunity(
    data: list[dict], total_size: int, record_count: int
) -> Issue | None:
    """Detect structural redundancy by measuring gzip compressibility."""
    if record_count == 0 or total_size == 0:
        return None

    raw_bytes = json.dumps(data, default=str).encode()
    compressed = gzip.compress(raw_bytes, compresslevel=6)
    compressed_size = len(compressed)

    reduction_ratio = round(1 - (compressed_size / total_size), 4)

    if reduction_ratio <= 0.5:
        return None

    savings_bytes = total_size - compressed_size
    # Weight compression impact lower since it's always the final step and
    # doesn't remove logical redundancy -- it just masks it in storage.
    impact_pct = round(reduction_ratio * 100 * 0.5, 2)

    return Issue(
        id="compression_opportunity",
        title=f"Dataset is {reduction_ratio:.0%} compressible ({savings_bytes:,} bytes recoverable)",
        severity="medium",
        impact_pct=impact_pct,
        impact_bytes=savings_bytes,
        description=(
            f"gzip reduces this dataset from {total_size:,} to {compressed_size:,} bytes "
            f"({reduction_ratio:.0%} reduction), indicating high structural redundancy."
        ),
        explanation=(
            "JSON and CSV carry significant structural overhead: repeated key names "
            "on every record, quote delimiters, commas, and braces that follow "
            "predictable patterns. gzip exploits this via LZ77 (replacing repeated "
            "byte sequences with back-references to earlier occurrences) followed by "
            "Huffman coding (assigning shorter bit patterns to frequent symbols). A "
            "compression ratio above 50% signals that the majority of the payload is "
            "structural boilerplate rather than information content. Compression is "
            "nearly always worth enabling for storage and network transfer, but it "
            "trades CPU cycles for space -- for hot-path serving, consider columnar "
            "formats that eliminate structural redundancy at the schema level instead."
        ),
        affected_fields=[],
        fix_stage="compress",
        projected_1m=_project_to_1m(savings_bytes, record_count),
    )


def analyze(data: list[dict]) -> IssueReport:
    """Analyze a dataset and return all detected issues."""
    total_size = len(json.dumps(data, default=str).encode())
    record_count = len(data)
    field_count = len(data[0]) if data else 0

    issues = []

    # 1. Detect duplicate records
    dup_issue = _detect_duplicates(data, total_size, record_count)
    if dup_issue:
        issues.append(dup_issue)

    # 2. Detect high string repetition
    rep_issue = _detect_repetition(data, total_size, record_count)
    if rep_issue:
        issues.append(rep_issue)

    # 3. Detect excess whitespace
    ws_issue = _detect_whitespace(data, total_size, record_count)
    if ws_issue:
        issues.append(ws_issue)

    # 4. Detect compression opportunity
    comp_issue = _detect_compression_opportunity(data, total_size, record_count)
    if comp_issue:
        issues.append(comp_issue)

    # Sort by impact
    issues.sort(key=lambda i: i.impact_pct, reverse=True)
    primary = issues[0] if issues else None

    # Calculate efficiency score (100 = no issues, lower = more waste)
    total_waste_pct = sum(i.impact_pct for i in issues)
    efficiency_score = max(0, min(100, round(100 - total_waste_pct)))

    return IssueReport(
        total_size=total_size,
        record_count=record_count,
        field_count=field_count,
        issues=issues,
        primary_issue=primary,
        efficiency_score=efficiency_score,
    )
