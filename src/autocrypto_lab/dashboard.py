"""Lightweight local dashboard rendering over reports and ledgers."""

from __future__ import annotations

import html
from pathlib import Path

from autocrypto_lab.ledger import read_ledger


def render_dashboard(report_paths: list[Path], ledger_path: Path) -> str:
    reports = "\n".join(f"<li>{html.escape(path.name)}</li>" for path in report_paths)
    ledger_rows = read_ledger(ledger_path)
    decisions = "\n".join(
        f"<tr><td>{html.escape(row.get('run_id', ''))}</td><td>{html.escape(row.get('hypothesis', ''))}</td><td>{html.escape(row.get('decision', ''))}</td></tr>"
        for row in ledger_rows
    )
    return f"""<!doctype html>
<html><head><meta charset=\"utf-8\"><title>Autocrypto Lab Dashboard</title></head>
<body>
<h1>Autocrypto Lab Dashboard</h1>
<p>Research diagnostics only; not investment advice.</p>
<h2>Reports</h2><ul>{reports}</ul>
<h2>Autonomous Ledger</h2>
<table><thead><tr><th>Run</th><th>Hypothesis</th><th>Decision</th></tr></thead><tbody>{decisions}</tbody></table>
</body></html>"""


def write_dashboard(path: Path, report_paths: list[Path], ledger_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_dashboard(report_paths, ledger_path), encoding="utf-8")
