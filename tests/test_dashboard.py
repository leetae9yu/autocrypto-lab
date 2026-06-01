from pathlib import Path

from autocrypto_lab.dashboard import render_dashboard, write_dashboard
from autocrypto_lab.ledger import LedgerEntry, append_ledger


def test_dashboard_renders_report_and_ledger(tmp_path: Path):
    report = tmp_path / "report.md"
    report.write_text("# report")
    ledger = tmp_path / "ledger.jsonl"
    append_ledger(ledger, LedgerEntry(
        run_id="r1",
        hypothesis="test hypothesis",
        config_hash="abc",
        config_diff={"run_id": {"before": "base", "after": "r1"}},
        config_snapshot={"run_id": "r1"},
        rationale="because",
        metrics={"net_return": 0.1},
        decision="continue",
        evidence="fixture",
        raw_data_snapshot_ids=["raw1"],
        normalized_data_snapshot_ids=["norm1"],
        feature_table_id="features1",
        model_artifact_id="model1",
        signal_artifact_id="signals1",
    ))
    html = render_dashboard([report], ledger)
    assert "Autocrypto Lab Dashboard" in html
    assert "report.md" in html
    assert "test hypothesis" in html
    assert "not investment advice" in html.lower()


def test_write_dashboard(tmp_path: Path):
    path = tmp_path / "site" / "index.html"
    write_dashboard(path, [], tmp_path / "missing.jsonl")
    assert path.exists()
