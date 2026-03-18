"""FastAPI backend for the Entropy Engine web application."""

from __future__ import annotations

import json
import sys
import tempfile
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

# Ensure the project root is on sys.path so entropy package can be imported.
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

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

# Stage configuration -------------------------------------------------------
STAGES = [
    ("dedup", "DEDUPLICATION"),
    ("encode", "DICT ENCODING"),
    ("trim", "FIELD TRIMMING"),
    ("compress", "COMPRESSION"),
]


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

    def _sse_event(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

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
