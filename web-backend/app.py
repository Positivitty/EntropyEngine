"""FastAPI backend for the Entropy Engine web application."""

from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
import time
import uuid
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

# Ensure the project root is on sys.path so entropy package can be imported.
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from entropy.issues import analyze, Issue, IssueReport  # noqa: E402
from entropy.loader import load  # noqa: E402
from entropy.metrics import StageResult, compute_size  # noqa: E402
from entropy.transforms import (  # noqa: E402
    compress,
    deduplicate,
    dictionary_encode,
    field_trim,
)

app = FastAPI(title="Entropy Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory stores ----------------------------------------------------------
_uploads: dict[str, dict] = {}      # file_id -> upload metadata
_results: dict[str, dict] = {}      # file_id -> pipeline results
_analyses: dict[str, dict] = {}     # file_id -> analysis results
_simulations: dict[str, dict] = {}  # file_id -> simulation results
_optimized: dict[str, list] = {}    # file_id -> optimized data

# Stage configuration -------------------------------------------------------
STAGES = [
    ("dedup", "DEDUPLICATION"),
    ("encode", "DICT ENCODING"),
    ("trim", "FIELD TRIMMING"),
    ("compress", "COMPRESSION"),
]

# Mapping from issue_id to the stage key and transform function
ISSUE_STAGE_MAP = {
    "duplicate_records": "dedup",
    "string_repetition": "encode",
    "excess_whitespace": "trim",
    "compression_opportunity": "compress",
}


def _sse_event(event: str, data: dict) -> str:
    """Format a server-sent event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _run_stage(stage_key: str, data: list[dict]) -> tuple[list[dict] | bytes, int]:
    """Run a single transform stage and return (output_data, output_size)."""
    if stage_key == "dedup":
        result = deduplicate(data)
        return result, compute_size(result)
    elif stage_key == "encode":
        enc_result = dictionary_encode(data)
        return enc_result.encoded_data, compute_size(enc_result.encoded_data)
    elif stage_key == "trim":
        result = field_trim(data)
        return result, compute_size(result)
    elif stage_key == "compress":
        compressed = compress(data)
        return compressed, compute_size(compressed)
    else:
        return data, compute_size(data)


def _load_upload_data(file_id: str) -> list[dict]:
    """Load the original uploaded data for a given file_id."""
    if file_id not in _uploads:
        raise HTTPException(status_code=404, detail="File not found.")

    upload_info = _uploads[file_id]
    tmp_path = upload_info["tmp_path"]

    try:
        load_result = load(tmp_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Uploaded file no longer available.",
        )
    return load_result.data


def _issue_to_dict(issue: Issue) -> dict:
    """Convert an Issue dataclass to a JSON-serializable dict."""
    return asdict(issue)


def _report_to_dict(report: IssueReport) -> dict:
    """Convert an IssueReport dataclass to a JSON-serializable dict."""
    return asdict(report)


# ---------------------------------------------------------------------------
# POST /upload
# ---------------------------------------------------------------------------
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Accept a JSON or CSV file upload and store it for later processing."""
    filename = file.filename or "unknown"
    suffix = Path(filename).suffix.lower()

    if suffix not in (".json", ".csv"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {suffix}. Use .json or .csv.",
        )

    contents = await file.read()
    size_bytes = len(contents)

    # Write to a temp file so entropy.loader can read it
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(contents)
    tmp.close()

    # Load to validate and count records
    try:
        load_result = load(tmp.name)
    except Exception as exc:
        Path(tmp.name).unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc))

    file_id = uuid.uuid4().hex
    fmt = "json" if suffix == ".json" else "csv"

    _uploads[file_id] = {
        "file_id": file_id,
        "filename": filename,
        "size_bytes": size_bytes,
        "record_count": len(load_result.data),
        "format": fmt,
        "tmp_path": tmp.name,
    }

    return JSONResponse(
        {
            "file_id": file_id,
            "filename": filename,
            "size_bytes": size_bytes,
            "record_count": len(load_result.data),
            "format": fmt,
        }
    )


# ---------------------------------------------------------------------------
# POST /process/{file_id}
# ---------------------------------------------------------------------------
@app.post("/process/{file_id}")
async def process_file(file_id: str):
    """Run the optimization pipeline and stream progress as SSE."""
    if file_id not in _uploads:
        raise HTTPException(status_code=404, detail="File not found.")

    upload_info = _uploads[file_id]
    tmp_path = upload_info["tmp_path"]

    try:
        load_result = load(tmp_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Uploaded file no longer available.",
        )

    def _generate():
        data = load_result.data
        original_size = compute_size(data)
        stage_results: list[dict] = []

        for stage_key, display_name in STAGES:
            input_size = compute_size(data)

            # stage_start
            yield _sse_event("stage_start", {
                "stage": stage_key,
                "input_size": input_size,
            })
            time.sleep(0.05)

            # Simulate progress updates
            for pct in (10, 25, 45, 65, 80, 95):
                yield _sse_event("stage_progress", {
                    "stage": stage_key,
                    "progress": pct,
                })
                time.sleep(0.05)

            # Run actual transform
            if stage_key == "dedup":
                data = deduplicate(data)
                output_size = compute_size(data)
            elif stage_key == "encode":
                enc_result = dictionary_encode(data)
                data = enc_result.encoded_data
                output_size = compute_size(data)
            elif stage_key == "trim":
                data = field_trim(data)
                output_size = compute_size(data)
            elif stage_key == "compress":
                compressed = compress(data)
                output_size = compute_size(compressed)
            else:
                output_size = compute_size(data)

            reduction_pct = round(
                ((input_size - output_size) / input_size) * 100, 1
            ) if input_size > 0 else 0.0

            # 100 % progress
            yield _sse_event("stage_progress", {
                "stage": stage_key,
                "progress": 100,
            })
            time.sleep(0.05)

            stage_info = {
                "stage": stage_key,
                "input_size": input_size,
                "output_size": output_size,
                "reduction_pct": reduction_pct,
            }
            stage_results.append(stage_info)

            # stage_complete
            yield _sse_event("stage_complete", stage_info)
            time.sleep(0.05)

        final_size = stage_results[-1]["output_size"] if stage_results else original_size
        total_reduction_pct = round(
            ((original_size - final_size) / original_size) * 100, 1
        ) if original_size > 0 else 0.0

        pipeline_result = {
            "original_size": original_size,
            "final_size": final_size,
            "total_reduction_pct": total_reduction_pct,
            "stages": stage_results,
        }

        # Cache results
        _results[file_id] = pipeline_result

        yield _sse_event("pipeline_complete", pipeline_result)

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# GET /results/{file_id}
# ---------------------------------------------------------------------------
@app.get("/results/{file_id}")
async def get_results(file_id: str):
    """Return cached results for a previously processed file."""
    if file_id not in _results:
        if file_id not in _uploads:
            raise HTTPException(status_code=404, detail="File not found.")
        raise HTTPException(
            status_code=404,
            detail="File has not been processed yet.",
        )

    return JSONResponse(_results[file_id])


# ---------------------------------------------------------------------------
# POST /analyze/{file_id}
# ---------------------------------------------------------------------------
@app.post("/analyze/{file_id}")
async def analyze_file(file_id: str):
    """Run issue detection on the uploaded file and return an analysis report."""
    data = _load_upload_data(file_id)
    report = analyze(data)
    report_dict = _report_to_dict(report)

    # Cache the analysis
    _analyses[file_id] = report_dict

    return JSONResponse(report_dict)


# ---------------------------------------------------------------------------
# POST /simulate/{file_id}/{issue_id}
# ---------------------------------------------------------------------------
@app.post("/simulate/{file_id}/{issue_id}")
async def simulate_fix(file_id: str, issue_id: str):
    """Simulate fixing a single issue without mutating original data.

    Streams SSE events for the single relevant stage, then returns
    the simulated size and reduction.
    """
    if issue_id not in ISSUE_STAGE_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown issue_id: {issue_id}. "
                   f"Valid values: {', '.join(ISSUE_STAGE_MAP.keys())}",
        )

    data = _load_upload_data(file_id)
    stage_key = ISSUE_STAGE_MAP[issue_id]

    # Find display name for this stage
    display_name = next(
        (name for key, name in STAGES if key == stage_key),
        stage_key.upper(),
    )

    def _generate():
        input_size = compute_size(data)

        # stage_start
        yield _sse_event("stage_start", {
            "stage": stage_key,
            "input_size": input_size,
        })
        time.sleep(0.05)

        # Simulate progress updates
        for pct in (10, 25, 45, 65, 80, 95):
            yield _sse_event("stage_progress", {
                "stage": stage_key,
                "progress": pct,
            })
            time.sleep(0.05)

        # Run the single transform
        output_data, output_size = _run_stage(stage_key, data)

        reduction_pct = round(
            ((input_size - output_size) / input_size) * 100, 1
        ) if input_size > 0 else 0.0

        # 100% progress
        yield _sse_event("stage_progress", {
            "stage": stage_key,
            "progress": 100,
        })
        time.sleep(0.05)

        stage_info = {
            "stage": stage_key,
            "input_size": input_size,
            "output_size": output_size,
            "reduction_pct": reduction_pct,
        }

        # stage_complete
        yield _sse_event("stage_complete", stage_info)
        time.sleep(0.05)

        # simulation_complete with summary
        sim_result = {
            "issue_id": issue_id,
            "original_size": input_size,
            "simulated_size": output_size,
            "reduction_bytes": input_size - output_size,
            "reduction_pct": reduction_pct,
            "stage": stage_key,
        }

        # Cache simulation result
        _simulations.setdefault(file_id, {})[issue_id] = sim_result

        yield _sse_event("simulation_complete", sim_result)

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# POST /apply/{file_id}
# ---------------------------------------------------------------------------
@app.post("/apply/{file_id}")
async def apply_fixes(file_id: str):
    """Apply all fixes (run the full pipeline) and store the optimized data."""
    data = _load_upload_data(file_id)

    original_size = compute_size(data)

    # Run all 4 transforms in sequence
    data = deduplicate(data)
    size_after_dedup = compute_size(data)

    enc_result = dictionary_encode(data)
    data = enc_result.encoded_data
    size_after_encode = compute_size(data)

    data = field_trim(data)
    size_after_trim = compute_size(data)

    compressed = compress(data)
    final_size = compute_size(compressed)

    # Store the optimized (pre-compression) data for export
    _optimized[file_id] = data

    total_reduction_pct = round(
        ((original_size - final_size) / original_size) * 100, 1
    ) if original_size > 0 else 0.0

    result = {
        "original_size": original_size,
        "final_size": final_size,
        "total_reduction_pct": total_reduction_pct,
        "stages": [
            {
                "stage": "dedup",
                "input_size": original_size,
                "output_size": size_after_dedup,
                "reduction_pct": round(
                    ((original_size - size_after_dedup) / original_size) * 100, 1
                ) if original_size > 0 else 0.0,
            },
            {
                "stage": "encode",
                "input_size": size_after_dedup,
                "output_size": size_after_encode,
                "reduction_pct": round(
                    ((size_after_dedup - size_after_encode) / size_after_dedup) * 100, 1
                ) if size_after_dedup > 0 else 0.0,
            },
            {
                "stage": "trim",
                "input_size": size_after_encode,
                "output_size": size_after_trim,
                "reduction_pct": round(
                    ((size_after_encode - size_after_trim) / size_after_encode) * 100, 1
                ) if size_after_encode > 0 else 0.0,
            },
            {
                "stage": "compress",
                "input_size": size_after_trim,
                "output_size": final_size,
                "reduction_pct": round(
                    ((size_after_trim - final_size) / size_after_trim) * 100, 1
                ) if size_after_trim > 0 else 0.0,
            },
        ],
    }

    return JSONResponse(result)


# ---------------------------------------------------------------------------
# GET /export/{file_id}
# ---------------------------------------------------------------------------
@app.get("/export/{file_id}")
async def export_data(
    file_id: str,
    format: str = Query("json", regex="^(json|csv)$"),
    type: str = Query("data", regex="^(data|report)$"),
):
    """Export optimized data or a full analysis report.

    Query params:
        format: "json" or "csv" (only applies to type=data)
        type: "data" for the optimized dataset, "report" for a full report
    """
    if file_id not in _uploads:
        raise HTTPException(status_code=404, detail="File not found.")

    upload_info = _uploads[file_id]
    base_name = Path(upload_info["filename"]).stem

    if type == "report":
        # Build a comprehensive report
        report_data: dict = {
            "file": {
                "filename": upload_info["filename"],
                "original_size_bytes": upload_info["size_bytes"],
                "record_count": upload_info["record_count"],
                "format": upload_info["format"],
            },
            "analysis": _analyses.get(file_id),
            "simulations": _simulations.get(file_id),
            "pipeline_results": _results.get(file_id),
        }

        content = json.dumps(report_data, indent=2, default=str)
        return StreamingResponse(
            iter([content]),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{base_name}_report.json"',
            },
        )

    # type == "data"
    if file_id not in _optimized:
        raise HTTPException(
            status_code=404,
            detail="No optimized data available. Run /apply/{file_id} first.",
        )

    data = _optimized[file_id]

    if format == "json":
        content = json.dumps(data, indent=2, default=str)
        return StreamingResponse(
            iter([content]),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{base_name}_optimized.json"',
            },
        )

    # format == "csv"
    if not data:
        csv_content = ""
    else:
        output = io.StringIO()
        # Gather all field names across all rows
        fieldnames: list[str] = []
        seen_fields: set[str] = set()
        for row in data:
            for key in row:
                if key not in seen_fields:
                    fieldnames.append(key)
                    seen_fields.add(key)
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        csv_content = output.getvalue()

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{base_name}_optimized.csv"',
        },
    )
