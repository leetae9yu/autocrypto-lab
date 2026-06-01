from pathlib import Path

from autocrypto_lab.autonomous import config_diff, evaluate_candidate_configs, generate_candidate_configs, pareto_decision, propose_config_variant, run_autonomous_config_loop, run_dry_iteration, run_iterative_agent_loop
from autocrypto_lab.config import ALLOWED_CONFIG_KEYS, CPU_FRIENDLY_MODELS, load_config
from autocrypto_lab.ledger import read_ledger
from test_public_binance_pipeline import FakeBinanceAdapter, ts


def test_propose_config_variant_only_changes_config():
    base = {"run_id": "base", "factors": ["momentum"], "interval": "1h"}
    variant = propose_config_variant(base, "volatility improves robustness")
    assert variant is not base
    assert variant["run_id"] == "base_agent_variant"
    assert "volatility" in variant["factors"]
    assert variant["metadata"]["hypothesis"]


def test_pareto_decision_rejects_single_metric_without_diagnostics():
    decision = pareto_decision({"net_return": 1.0, "max_drawdown": -0.5, "turnover": 1.0}, {"net_return": 0.1, "max_drawdown": -0.1, "turnover": 1.0})
    assert decision == "defer"


def test_config_diff_records_before_after_values():
    diff = config_diff({"run_id": "base", "factors": ["momentum"]}, {"run_id": "variant", "factors": ["momentum", "volatility"]})
    assert diff["run_id"] == {"before": "base", "after": "variant"}
    assert diff["factors"]["after"] == ["momentum", "volatility"]


def test_generate_candidate_configs_is_deterministic_and_budgeted():
    base = {"run_id": "base", "symbols": ["BTC", "ETH"], "interval": "1h", "factors": ["momentum"]}

    first = generate_candidate_configs(base, max_candidates=3)
    second = generate_candidate_configs(base, max_candidates=3)

    assert first == second
    assert [candidate["candidate_id"] for candidate in first] == [
        "candidate_001_weighted_score_baseline",
        "candidate_002_equal_weight_robustness",
        "candidate_003_sign_weight_directional",
    ]
    assert len(first) == 3


def test_generate_candidate_configs_are_config_only_and_cpu_safe():
    candidates = generate_candidate_configs({"run_id": "base", "interval": "1h", "factors": ["momentum"]}, max_candidates=8)

    assert {candidate["config"]["model"] for candidate in candidates} <= set(CPU_FRIENDLY_MODELS)
    assert any(candidate["config"]["model"] == "walk_forward_equal_weight_score" for candidate in candidates)
    assert any("reversal" in candidate["config"]["factors"] for candidate in candidates if isinstance(candidate["config"].get("factors"), list))
    for candidate in candidates:
        config = candidate["config"]
        assert set(config) <= set(ALLOWED_CONFIG_KEYS)
        assert config["public_only"] is True
        assert config["allow_private_read"] is False
        assert config["allow_trading"] is False
        load_config(config)


def test_generate_candidate_configs_rejects_unknown_base_keys():
    try:
        generate_candidate_configs({"run_id": "base", "surprise": "nope"}, max_candidates=1)
    except ValueError as exc:
        assert "unknown config keys" in str(exc)
    else:
        raise AssertionError("unknown base config key was accepted")


def test_evaluate_candidate_configs_runs_real_walk_forward_pipeline(tmp_path: Path):
    summary = evaluate_candidate_configs(
        tmp_path,
        {
            "run_id": "agent_eval",
            "symbols": ["BTC", "ETH"],
            "interval": "1h",
            "factors": ["momentum", "derivatives_pressure"],
        },
        start=ts(0),
        end=ts(3),
        adapter=FakeBinanceAdapter(),
        max_candidates=2,
        train_periods=2,
        test_periods=1,
    )

    assert summary["candidate_count"] == 2
    assert summary["best_candidate_id"]
    assert Path(summary["summary_path"]).exists()
    assert Path(summary["ledger_path"]).exists()
    assert [row["candidate_id"] for row in summary["evaluations"]] == [
        "candidate_001_weighted_score_baseline",
        "candidate_002_equal_weight_robustness",
    ]
    for row in summary["evaluations"]:
        assert Path(row["artifact_paths"]["manifest"]).exists()
        assert Path(row["artifact_paths"]["metrics"]).exists()
        assert row["artifact_lineage"]["model_artifact_id"]
        assert row["metrics"]["factor_model"].startswith(row["run_id"])
        assert row["walk_forward"] == {"train_periods": 2, "test_periods": 1, "step_periods": None}
        assert row["decision"] in {"adopt", "continue", "defer"}
        assert row["pareto_rank"] in {1, 2}
    ledger_rows = read_ledger(Path(summary["ledger_path"]))
    assert len(ledger_rows) == 2
    assert ledger_rows[0]["candidate_id"] == "candidate_001_weighted_score_baseline"
    assert ledger_rows[0]["parent_run_id"] == "agent_eval"
    assert ledger_rows[0]["model_family"] == "walk_forward_weighted_score"
    assert ledger_rows[0]["manifest_path"].endswith("manifest.json")
    assert ledger_rows[0]["dashboard_path"].endswith("dashboard.html")
    assert ledger_rows[0]["pareto_rank"] in {1, 2}


def test_run_iterative_agent_loop_promotes_feedback_into_next_config(tmp_path: Path):
    summary = run_iterative_agent_loop(
        tmp_path,
        {
            "run_id": "agent_iter",
            "symbols": ["BTC", "ETH"],
            "interval": "1h",
            "factors": ["momentum", "derivatives_pressure"],
        },
        start=ts(0),
        end=ts(3),
        adapter=FakeBinanceAdapter(),
        iterations=2,
        max_candidates=2,
        train_periods=2,
        test_periods=1,
    )

    assert summary["iterations_completed"] == 2
    assert Path(summary["summary_path"]).exists()
    assert summary["iteration_summaries"][0]["promoted_candidate_id"]
    assert summary["iteration_summaries"][1]["base_run_id"] == "agent_iter_iteration_002_base"
    ledger_rows = read_ledger(Path(summary["ledger_path"]))
    assert len(ledger_rows) == 4
    assert {row["parent_run_id"] for row in ledger_rows} == {"agent_iter", "agent_iter_iteration_002_base"}
    iteration_1 = Path(summary["iteration_summaries"][0]["summary_path"])
    first_summary = __import__("json").loads(iteration_1.read_text())
    assert first_summary["next_base_config"]["metadata"]["promoted_from_candidate_id"] == first_summary["promoted_candidate_id"]


def test_dry_iteration_writes_required_ledger_fields(tmp_path: Path):
    result = run_dry_iteration(
        tmp_path / "ledger.jsonl",
        {"run_id": "base", "factors": ["momentum"], "interval": "1h"},
        {"net_return_after_funding": 0.01, "max_drawdown": -0.1, "turnover": 1.0, "ic": 0.1, "quantile_returns": {"q1": 0.0}},
        {"net_return_after_funding": 0.02, "max_drawdown": -0.05, "turnover": 1.0, "ic": 0.2, "quantile_returns": {"q1": 0.0, "q3": 0.01}},
        "volatility improves robustness",
        artifact_ids={
            "raw_data_snapshot_ids": ["raw1"],
            "normalized_data_snapshot_ids": ["norm1"],
            "feature_table_id": "features1",
            "model_artifact_id": "model1",
            "signal_artifact_id": "signals1",
        },
    )
    assert result["decision"] == "adopt"
    rows = read_ledger(tmp_path / "ledger.jsonl")
    assert rows[0]["rationale"]
    assert rows[0]["config_hash"]
    assert rows[0]["config_diff"]["factors"]["after"] == ["momentum", "volatility"]
    assert rows[0]["config_snapshot"]["run_id"] == "base_agent_variant"
    assert rows[0]["raw_data_snapshot_ids"] == ["raw1"]
    assert rows[0]["normalized_data_snapshot_ids"] == ["norm1"]
    assert rows[0]["feature_table_id"] == "features1"
    assert rows[0]["model_artifact_id"] == "model1"
    assert rows[0]["signal_artifact_id"] == "signals1"
    assert rows[0]["decision"] == "adopt"


def test_autonomous_config_loop_records_repeated_artifact_provenance(tmp_path: Path):
    ledger = tmp_path / "ledger.jsonl"
    results = run_autonomous_config_loop(
        ledger,
        {"run_id": "base", "factors": ["momentum"], "interval": "1h"},
        {"net_return_after_funding": 0.01, "max_drawdown": -0.1, "turnover": 1.0, "ic": 0.1, "quantile_returns": {"q1": 0.0}},
        [
            {
                "hypothesis": "add volatility improves risk",
                "metrics": {"net_return_after_funding": 0.02, "max_drawdown": -0.05, "turnover": 1.0, "ic": 0.2, "quantile_returns": {"q1": 0.0}},
                "artifact_ids": {"raw_data_snapshot_ids": ["raw-a"], "normalized_data_snapshot_ids": ["norm-a"], "feature_table_id": "ft-a", "model_artifact_id": "model-a", "signal_artifact_id": "sig-a"},
            },
            {
                "hypothesis": "bad sparse diagnostic should defer",
                "metrics": {"net_return_after_funding": 0.5, "max_drawdown": -0.9, "turnover": 99.0, "ic": 0.0, "quantile_returns": {}},
                "artifact_ids": {"raw_data_snapshot_ids": ["raw-b"], "normalized_data_snapshot_ids": ["norm-b"], "feature_table_id": "ft-b", "model_artifact_id": "model-b", "signal_artifact_id": "sig-b"},
            },
        ],
    )
    rows = read_ledger(ledger)
    assert [row["decision"] for row in rows] == ["adopt", "defer"]
    assert len(results) == 2
    assert rows[0]["model_artifact_id"] == "model-a"
    assert rows[1]["signal_artifact_id"] == "sig-b"
    assert rows[0]["config_diff"]


def test_generate_candidate_configs_includes_low_turnover_rebalance_templates():
    candidates = generate_candidate_configs(
        {"run_id": "base", "symbols": ["BTC", "ETH"], "interval": "1h", "factors": ["momentum", "volatility"]},
        max_candidates=12,
    )
    low_turnover = [candidate for candidate in candidates if candidate["config"].get("model_params", {}).get("backtest_rebalance_periods", 1) > 1]
    assert low_turnover
    assert any(candidate["config"].get("horizon_periods") == 24 for candidate in low_turnover)
    for candidate in low_turnover:
        load_config(candidate["config"])

