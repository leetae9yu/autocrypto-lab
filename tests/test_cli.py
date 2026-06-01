from autocrypto_lab import __version__
from autocrypto_lab.cli import main


def test_version_exists():
    assert __version__ == "0.1.0"


def test_cli_help(capsys):
    assert main([]) == 0
    assert "Local-first crypto quant" in capsys.readouterr().out


def test_sample_info(capsys):
    assert main(["sample-info"]) == 0
    assert "ohlcv_1h.csv" in capsys.readouterr().out


def test_cli_run_public_fixture(tmp_path, capsys):
    assert main(["run-public-fixture", "--output-dir", str(tmp_path), "--run-id", "cli_public"]) == 0
    out = capsys.readouterr().out
    assert "model:" in out
    assert (tmp_path / "models" / "cli_public_weighted_score.model.json").exists()
