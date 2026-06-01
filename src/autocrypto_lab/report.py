"""Markdown report generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

DISCLAIMER = "Research diagnostics only; not investment advice or a profit guarantee."


def write_markdown_report(path: Path, run_id: str, metrics: dict[str, Any], limitations: list[str] | None = None) -> None:
    limitations = limitations or ["Short samples and overlapping regimes can distort interpretation."]
    path.parent.mkdir(parents=True, exist_ok=True)
    metric_lines = "\n".join(f"- {key}: {value}" for key, value in sorted(metrics.items()))
    limitation_lines = "\n".join(f"- {item}" for item in limitations)
    path.write_text(
        f"# Autocrypto Lab Report: {run_id}\n\n"
        f"> {DISCLAIMER}\n\n"
        "## Metrics\n\n"
        f"{metric_lines}\n\n"
        "## Limitations\n\n"
        f"{limitation_lines}\n",
        encoding="utf-8",
    )
