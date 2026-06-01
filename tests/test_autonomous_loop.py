from pathlib import Path

from autocrypto_lab.autonomous import config_diff, generate_candidate_configs, pareto_decision, propose_config_variant, run_autonomous_config_loop, run_dry_iteration
from autocrypto_lab.config import ALLOWED_CONFIG_KEYS, CPU_FRIENDLY_MODELS, load_config
from autocrypto_lab.ledger import read_ledger


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
