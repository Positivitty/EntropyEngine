"""Pipeline orchestrator for sequential entropy reduction stages."""

from __future__ import annotations

import time
from typing import Callable

from entropy.metrics import StageResult, compute_size
from entropy.transforms import (
    compress,
    deduplicate,
    dictionary_encode,
    field_trim,
)


class Pipeline:
    """Runs all four transformation stages sequentially and tracks metrics.

    Args:
        on_stage_progress: Optional callback invoked during each stage with
            (stage_name, progress_pct) to drive UI progress bars.
        on_stage_complete: Optional callback invoked after each stage finishes
            with the StageResult for that stage.
    """

    STAGES = ["deduplicate", "dictionary_encode", "field_trim", "compress"]

    def __init__(
        self,
        on_stage_progress: Callable[[str, float], None] | None = None,
        on_stage_complete: Callable[[StageResult], None] | None = None,
    ) -> None:
        self._on_progress = on_stage_progress
        self._on_complete = on_stage_complete

    def run(self, data: list[dict]) -> tuple[list[StageResult], int]:
        """Execute all pipeline stages on the input data.

        Args:
            data: List of dicts to process.

        Returns:
            A tuple of (list of StageResult for each stage, final compressed
            size in bytes).
        """
        results: list[StageResult] = []
        current_data: list[dict] = data
        final_compressed_size = 0

        for stage_name in self.STAGES:
            input_size = compute_size(current_data)
            self._simulate_progress(stage_name)

            if stage_name == "deduplicate":
                current_data = deduplicate(current_data)
                output_size = compute_size(current_data)

            elif stage_name == "dictionary_encode":
                encode_result = dictionary_encode(current_data)
                current_data = encode_result.encoded_data
                output_size = compute_size(current_data)

            elif stage_name == "field_trim":
                current_data = field_trim(current_data)
                output_size = compute_size(current_data)

            elif stage_name == "compress":
                compressed = compress(current_data)
                output_size = compute_size(compressed)
                final_compressed_size = output_size

            reduction = _reduction_pct(input_size, output_size)
            result = StageResult(
                stage_name=stage_name,
                input_size=input_size,
                output_size=output_size,
                reduction_pct=reduction,
            )
            results.append(result)

            if self._on_complete:
                self._on_complete(result)

        return results, final_compressed_size

    def _simulate_progress(self, stage_name: str) -> None:
        """Send simulated progress updates with small delays for animation."""
        if not self._on_progress:
            return

        steps = [0, 10, 25, 45, 65, 80, 90, 100]
        for pct in steps:
            self._on_progress(stage_name, pct)
            if pct < 100:
                time.sleep(0.03)


def _reduction_pct(input_size: int, output_size: int) -> float:
    """Calculate percentage reduction between input and output sizes."""
    if input_size == 0:
        return 0.0
    return round((1 - output_size / input_size) * 100, 2)
