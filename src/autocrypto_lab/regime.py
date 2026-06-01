"""ETF multi-window regime diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from autocrypto_lab.backtest import research_diagnostics
from autocrypto_lab.etf import EventWindow, default_etf_windows
from autocrypto_lab.report import DISCLAIMER


def rows_in_window(rows: list[dict[str, Any]], window: EventWindow) -> list[dict[str, Any]]:
    return [row for row in rows if window.start <= row["timestamp"].date() <= window.end]


def regime_metrics(rows: list[dict[str, Any]], factor: str = "momentum", windows: tuple[EventWindow, ...] | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for window in windows or default_etf_windows():
        subset = rows_in_window(rows, window)
        metrics = research_diagnostics(subset, factor) if subset else {"periods": 0, "net_return": 0.0, "ic": 0.0, "max_drawdown": 0.0, "turnover": 0.0, "quantile_returns": {}}
        out.append({"window": window, "metrics": metrics})
    return out


def write_regime_report(path: Path, rows: list[dict[str, Any]], factor: str = "momentum") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sections = [f"# ETF Regime Diagnostics\n\n> {DISCLAIMER}\n"]
    for item in regime_metrics(rows, factor=factor):
        window = item["window"]
        metrics = item["metrics"]
        sections.append(
            f"## {window.name}\n\n"
            f"- Anchor: {window.anchor_date}\n"
            f"- Window: {window.start} to {window.end}\n"
            f"- Interpretation: {window.interpretation}\n"
            f"- Sources: {', '.join(source.url for source in window.sources)}\n"
            f"- IC: {metrics.get('ic', 0.0)}\n"
            f"- Net return: {metrics.get('net_return', 0.0)}\n"
            f"- Max drawdown: {metrics.get('max_drawdown', 0.0)}\n"
            f"- Turnover: {metrics.get('turnover', 0.0)}\n"
            f"- Quantile returns: {metrics.get('quantile_returns', {})}\n"
        )
    sections.append("## Limitations\n\n- ETF samples are short.\n- Macro regimes overlap the ETF launch period.\n- Diagnostics are not investment advice.\n")
    path.write_text("\n".join(sections), encoding="utf-8")
