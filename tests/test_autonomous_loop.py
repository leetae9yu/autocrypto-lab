from pathlib import Path

from autocrypto_lab.autonomous import config_diff, pareto_decision, propose_config_variant, run_dry_iteration
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


def test_dry_iteration_writes_required_ledger_fields(tmp_path: Path):
    result = run_dry_iteration(
        tmp_path / "ledger.jsonl",
        {"run_id": "base", "factors": ["momentum"], "interval": "1h"},
        {"net_return_after_funding": 0.01, "max_drawdown": -0.1, "turnover": 1.0, "ic": 0.1, "quantile_returns": {"q1": 0.0}},
        {"net_return_after_funding": 0.02, "max_drawdown": -0.05, "turnover": 1.0, "ic": 0.2, "quantile_returns": {"q1": 0.0, "q3": 0.01}},
        "volatility improves robustness",
    )
    assert result["decision"] == "adopt"
    rows = read_ledger(tmp_path / "ledger.jsonl")
    assert rows[0]["rationale"]
    assert rows[0]["config_hash"]
    assert rows[0]["config_diff"]["factors"]["after"] == ["momentum", "volatility"]
    assert rows[0]["config_snapshot"]["run_id"] == "base_agent_variant"
    assert rows[0]["decision"] == "adopt"
