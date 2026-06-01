from pathlib import Path

from autocrypto_lab.pipeline import run_fixture_pipeline
from autocrypto_lab.report import DISCLAIMER


def test_fixture_pipeline_outputs_report_and_manifest(tmp_path: Path):
    outputs = run_fixture_pipeline(
        Path("tests/fixtures/ohlcv_1h.csv"),
        tmp_path,
        {"run_id": "pytest_smoke", "symbols": ["BTC", "ETH"], "interval": "1h"},
    )
    assert outputs["report"].exists()
    assert outputs["manifest"].exists()
    report = outputs["report"].read_text()
    assert DISCLAIMER in report
    assert "net_return" in report


def test_cli_run_sample(tmp_path: Path, capsys):
    from autocrypto_lab.cli import main

    assert main(["run-sample", "--output-dir", str(tmp_path), "--run-id", "cli_smoke"]) == 0
    out = capsys.readouterr().out
    assert "report:" in out
    assert (tmp_path / "report.md").exists()
