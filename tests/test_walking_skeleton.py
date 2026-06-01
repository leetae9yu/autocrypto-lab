from pathlib import Path
import json

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
    assert outputs["regime_report"].exists()
    assert outputs["dashboard"].exists()
    report = outputs["report"].read_text()
    assert DISCLAIMER in report
    assert "net_return" in report
    manifest = json.loads(outputs["manifest"].read_text())
    assert manifest["source_metadata"]["factor_specs"][0]["name"] == "momentum"


def test_fixture_pipeline_uses_config_factor_dsl(tmp_path: Path):
    outputs = run_fixture_pipeline(
        Path("tests/fixtures/ohlcv_1h.csv"),
        tmp_path,
        {
            "run_id": "pytest_volatility",
            "symbols": ["BTC", "ETH"],
            "interval": "1h",
            "factors": [{"name": "volatility", "params": {"lookback": 2}}],
        },
    )
    report = outputs["report"].read_text()
    manifest = json.loads(outputs["manifest"].read_text())
    assert "- factor: volatility" in report
    assert manifest["source_metadata"]["factor_specs"] == [{"name": "volatility", "params": {"lookback": 2}}]


def test_cli_run_sample(tmp_path: Path, capsys):
    from autocrypto_lab.cli import main

    assert main(["run-sample", "--output-dir", str(tmp_path), "--run-id", "cli_smoke"]) == 0
    out = capsys.readouterr().out
    assert "report:" in out
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "regime_report.md").exists()
    assert (tmp_path / "dashboard.html").exists()
