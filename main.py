"""Entropy Engine - Data entropy reduction pipeline.

Usage:
    python main.py input.json
    python main.py samples/sample.csv --no-animation
"""

import argparse
import sys

from entropy import loader
from entropy.metrics import StageResult, compute_size
from entropy.transforms import compress, deduplicate, dictionary_encode, field_trim
from ui.terminal import EntropyTerminal


STAGES = [
    ("dedup", "Detecting redundancy...", deduplicate),
    ("encode", "Analyzing string frequency...", None),  # special handling
    ("trim", "Scanning for dead weight...", field_trim),
    ("compress", "Applying entropy compression...", None),  # special handling
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Entropy Engine: reduce data entropy through a multi-stage pipeline.",
    )
    parser.add_argument("file", help="Path to a .json or .csv data file.")
    parser.add_argument(
        "--no-animation", action="store_true", default=False,
        help="Skip terminal animation delays.",
    )
    args = parser.parse_args()

    terminal = EntropyTerminal(animate=not args.no_animation)

    # Boot
    terminal.boot_sequence()

    # Load
    try:
        result = loader.load(args.file)
    except FileNotFoundError:
        terminal.show_error(f"File not found: {args.file}")
        sys.exit(1)
    except ValueError as exc:
        terminal.show_error(str(exc))
        sys.exit(1)

    terminal.show_file_info(
        filename=result.source_path,
        size=result.original_size_bytes,
        record_count=len(result.data),
        fmt=result.format,
    )

    # Pipeline diagram
    terminal.show_pipeline_diagram()
    terminal.log("RUNNING OPTIMIZATION PIPELINE...")
    terminal.console.print()

    # Run stages
    data = result.data
    stages: list[StageResult] = []

    for stage_key, log_msg, transform_fn in STAGES:
        input_size = compute_size(data)

        terminal.log(log_msg)
        terminal.show_pipeline_diagram(active_stage=stage_key)
        terminal.animate_stage(stage_key)

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

        reduction = round((1 - output_size / input_size) * 100, 2) if input_size else 0.0
        sr = StageResult(stage_key, input_size, output_size, reduction)
        stages.append(sr)
        terminal.show_stage_result(sr)

    # Summary
    original_bytes = result.original_size_bytes
    final_bytes = stages[-1].output_size if stages else original_bytes
    terminal.show_summary(stages, original_bytes, final_bytes)


if __name__ == "__main__":
    main()
