from autocrypto_lab import __version__
import autocrypto_lab.cli as cli
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


def test_cli_run_agent_loop_uses_public_autonomous_evaluator(tmp_path, capsys, monkeypatch):
    calls = {}

    def fake_evaluator(output_dir, base_config, **kwargs):
        calls["output_dir"] = output_dir
        calls["base_config"] = base_config
        calls["kwargs"] = kwargs
        return {
            "summary_path": str(tmp_path / "agent_loop_summary.json"),
            "ledger_path": str(tmp_path / "agent_ledger.jsonl"),
            "iterations_completed": 2,
            "iteration_summaries": [
                {
                    "iteration": 1,
                    "best_candidate_id": "candidate_001_weighted_score_baseline",
                    "promoted_candidate_id": "candidate_001_weighted_score_baseline",
                    "promoted_decision": "continue",
                    "candidate_count": 1,
                }
            ],
        }

    monkeypatch.setattr(cli, "run_iterative_agent_loop", fake_evaluator)

    assert main(
        [
            "run-agent-loop",
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "cli_agent",
            "--symbols",
            "BTC,ETH",
            "--factors",
            "momentum,derivatives_pressure",
            "--lookback-hours",
            "48",
            "--max-candidates",
            "1",
            "--iterations",
            "2",
        ]
    ) == 0

    out = capsys.readouterr().out
    assert "iterations_completed: 2" in out
    assert "iteration: 1 best=candidate_001_weighted_score_baseline promoted=candidate_001_weighted_score_baseline" in out
    assert calls["base_config"]["run_id"] == "cli_agent"
    assert calls["base_config"]["symbols"] == ["BTC", "ETH"]
    assert calls["base_config"]["factors"] == ["momentum", "derivatives_pressure"]
    assert calls["kwargs"]["max_candidates"] == 1
    assert calls["kwargs"]["iterations"] == 2
