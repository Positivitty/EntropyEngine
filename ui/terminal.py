"""Entropy Engine - Main terminal UI controller.

Dark, tactical, sci-fi terminal interface powered by rich.
"""

from __future__ import annotations

import time

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ui.theme import BOOT_MESSAGES, COLORS, STAGE_NAMES
from ui.animations import (
    pipeline_diagram,
    progress_bar,
    size_comparison,
    stage_header,
)
from entropy.metrics import StageResult, format_size


class EntropyTerminal:
    """Primary terminal renderer for the Entropy Engine pipeline."""

    def __init__(self, animate: bool = True) -> None:
        self.console = Console()
        self.animate = animate

    # ── Boot ───────────────────────────────────────────────────────────────

    def boot_sequence(self) -> None:
        """Display startup messages one by one with tactical delay."""
        self.console.print()
        for i, msg in enumerate(BOOT_MESSAGES):
            if i == len(BOOT_MESSAGES) - 1:
                if self.animate:
                    time.sleep(0.4)
                self.console.print(
                    f"  [bold {COLORS['primary']}]▸ {msg}[/bold {COLORS['primary']}]"
                )
            else:
                if self.animate:
                    time.sleep(0.15)
                self.console.print(f"  [{COLORS['primary']}]▸ {msg}[/{COLORS['primary']}]")
        self.console.print()

    # ── File Info ──────────────────────────────────────────────────────────

    def show_file_info(self, filename: str, size: int, record_count: int, fmt: str) -> None:
        """Display loaded file metadata."""
        panel = Panel(
            Text.from_markup(
                f"[{COLORS['accent']}]FILE:[/{COLORS['accent']}]     {filename}\n"
                f"[{COLORS['accent']}]FORMAT:[/{COLORS['accent']}]   {fmt.upper()}\n"
                f"[{COLORS['accent']}]SIZE:[/{COLORS['accent']}]     {format_size(size)}\n"
                f"[{COLORS['accent']}]RECORDS:[/{COLORS['accent']}]  {record_count}"
            ),
            border_style=COLORS["dim"],
            title=f"[{COLORS['primary']}]TARGET LOADED[/{COLORS['primary']}]",
            title_align="left",
            padding=(1, 2),
        )
        self.console.print(panel)

    # ── Pipeline Diagram ──────────────────────────────────────────────────

    def show_pipeline_diagram(self, active_stage: str | None = None) -> None:
        """Render the full pipeline with the active stage highlighted."""
        diagram = pipeline_diagram(active_stage)
        self.console.print()
        self.console.print(f"  {diagram}")
        self.console.print()

    # ── Stage Animation ───────────────────────────────────────────────────

    def animate_stage(self, stage_key: str) -> None:
        """Show stage header and animated progress bar.

        stage_key should be one of: dedup, encode, trim, compress
        """
        header = stage_header(stage_key)
        self.console.print(f"  [{COLORS['accent']}]{header}[/{COLORS['accent']}]")

        if not self.animate:
            self.console.print(
                f"  [{COLORS['primary']}]{progress_bar(100)}[/{COLORS['primary']}]"
            )
            return

        steps = [0, 5, 12, 20, 30, 42, 55, 68, 78, 85, 92, 100]
        with Live(
            Text.from_markup(f"  [{COLORS['primary']}]{progress_bar(0)}[/{COLORS['primary']}]"),
            console=self.console,
            refresh_per_second=20,
            transient=True,
        ) as live:
            for pct in steps:
                bar = progress_bar(pct)
                live.update(
                    Text.from_markup(f"  [{COLORS['primary']}]{bar}[/{COLORS['primary']}]")
                )
                if pct < 100:
                    time.sleep(0.06)

        # Print final bar permanently
        self.console.print(
            f"  [{COLORS['primary']}]{progress_bar(100)}[/{COLORS['primary']}]"
        )

    # ── Stage Result ──────────────────────────────────────────────────────

    def show_stage_result(self, result: StageResult) -> None:
        """Show completion line with size delta for a finished stage."""
        display = STAGE_NAMES.get(result.stage_name, result.stage_name.upper())
        comparison = size_comparison(result.input_size, result.output_size)
        self.console.print(
            f"  [{COLORS['accent']}]▸ {display} COMPLETE[/{COLORS['accent']}]  "
            f"[{COLORS['warning']}]{comparison}[/{COLORS['warning']}]"
        )
        self.console.print()

    # ── Final Summary ─────────────────────────────────────────────────────

    def show_summary(
        self,
        stages: list[StageResult],
        original_size: int,
        final_size: int,
    ) -> None:
        """Render the final summary table."""
        table = Table(
            title="ENTROPY REDUCTION REPORT",
            title_style=f"bold {COLORS['primary']}",
            border_style=COLORS["dim"],
            header_style=f"bold {COLORS['accent']}",
            show_lines=True,
            padding=(0, 1),
        )
        table.add_column("STAGE", style=COLORS["primary"])
        table.add_column("INPUT", justify="right", style=COLORS["accent"])
        table.add_column("OUTPUT", justify="right", style=COLORS["accent"])
        table.add_column("REDUCTION", justify="right", style=COLORS["warning"])

        for s in stages:
            display = STAGE_NAMES.get(s.stage_name, s.stage_name.upper())
            table.add_row(
                display,
                format_size(s.input_size),
                format_size(s.output_size),
                f"-{s.reduction_pct:.1f}%",
            )

        total_delta = ((original_size - final_size) / original_size * 100) if original_size else 0.0
        table.add_row(
            f"[bold {COLORS['primary']}]TOTAL[/bold {COLORS['primary']}]",
            f"[bold]{format_size(original_size)}[/bold]",
            f"[bold]{format_size(final_size)}[/bold]",
            f"[bold {COLORS['warning']}]-{total_delta:.1f}%[/bold {COLORS['warning']}]",
        )

        self.console.print()
        self.console.print(table)
        self.console.print()
        self.console.print(
            f"  [bold {COLORS['primary']}]▸ PIPELINE COMPLETE[/bold {COLORS['primary']}]"
        )
        self.console.print()

    # ── Error ──────────────────────────────────────────────────────────────

    def show_error(self, message: str) -> None:
        """Print an error message."""
        self.console.print(f"  [bold red]ERROR:[/bold red] {message}")

    # ── Log ───────────────────────────────────────────────────────────────

    def log(self, message: str) -> None:
        """Print a dim-green log line with > prefix."""
        self.console.print(
            f"  [{COLORS['dim']}]▸[/{COLORS['dim']}] [{COLORS['primary']}]{message}[/{COLORS['primary']}]"
        )
