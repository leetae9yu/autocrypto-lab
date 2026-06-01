"""Config-only autonomous research loop primitives."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from autocrypto_lab.ledger import LedgerEntry, append_ledger
from autocrypto_lab.manifest import stable_hash


def propose_config_variant(config: dict[str, Any], hypothesis: str) -> dict[str, Any]:
    """Return a config-only mutation for a hypothesis; never edits runtime code."""
    variant = copy.deepcopy(config)
    variant.setdefault("metadata", {})["hypothesis"] = hypothesis
    variant["run_id"] = f"{config.get('run_id', 'run')}_agent_variant"
    variant["fee_bps"] = float(config.get("fee_bps", 5.0))
    variant["slippage_bps"] = float(config.get("slippage_bps", 2.0))
    factors = list(variant.get("factors", ["momentum"]))
    if "volatility" not in factors:
        factors.append("volatility")
    variant["factors"] = factors
    return variant


def config_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Record top-level config changes for autonomous provenance."""
    keys = sorted(set(before) | set(after))
    diff: dict[str, Any] = {}
    for key in keys:
        old = before.get(key)
        new = after.get(key)
        if old != new:
            diff[key] = {"before": old, "after": new}
    return diff


def pareto_decision(candidate: dict[str, float], baseline: dict[str, float]) -> str:
    improves_return = candidate.get("net_return_after_funding", candidate.get("net_return", 0.0)) > baseline.get("net_return_after_funding", baseline.get("net_return", 0.0))
    improves_drawdown = candidate.get("max_drawdown", -1.0) >= baseline.get("max_drawdown", -1.0)
    turnover_ok = candidate.get("turnover", 999.0) <= max(2.0, baseline.get("turnover", 2.0) * 1.5)
    diagnostics_ok = candidate.get("ic", 0.0) != 0.0 and bool(candidate.get("quantile_returns"))
    if improves_return and improves_drawdown and turnover_ok and diagnostics_ok:
        return "adopt"
    if diagnostics_ok:
        return "continue"
    return "defer"


def run_dry_iteration(
    ledger_path: Path,
    config: dict[str, Any],
    baseline: dict[str, float],
    candidate: dict[str, float],
    hypothesis: str,
    *,
    artifact_ids: dict[str, Any] | None = None,
) -> dict[str, Any]:
    variant = propose_config_variant(config, hypothesis)
    decision = pareto_decision(candidate, baseline)
    artifacts = artifact_ids or {}
    entry = LedgerEntry(
        run_id=variant["run_id"],
        hypothesis=hypothesis,
        config_hash=stable_hash(variant),
        config_diff=config_diff(config, variant),
        config_snapshot=variant,
        rationale="config-only dry-run variant evaluated with Pareto + diagnostics policy",
        metrics=candidate,
        decision=decision,
        evidence="dry-run metrics supplied by fixture test",
        raw_data_snapshot_ids=list(artifacts.get("raw_data_snapshot_ids", [])),
        normalized_data_snapshot_ids=list(artifacts.get("normalized_data_snapshot_ids", [])),
        feature_table_id=str(artifacts.get("feature_table_id", "")),
        model_artifact_id=str(artifacts.get("model_artifact_id", "")),
        signal_artifact_id=str(artifacts.get("signal_artifact_id", "")),
    )
    append_ledger(ledger_path, entry)
    return {"variant": variant, "decision": decision, "config_hash": entry.config_hash}


def run_autonomous_config_loop(
    ledger_path: Path,
    base_config: dict[str, Any],
    baseline: dict[str, float],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run bounded config-only experiments supplied by a deterministic runner."""
    results: list[dict[str, Any]] = []
    current = copy.deepcopy(base_config)
    for idx, candidate in enumerate(candidates, start=1):
        hypothesis = str(candidate["hypothesis"])
        metrics = dict(candidate["metrics"])
        artifacts = dict(candidate.get("artifact_ids", {}))
        variant_seed = {**current, "run_id": f"{base_config.get('run_id', 'run')}_agent_{idx}"}
        result = run_dry_iteration(ledger_path, variant_seed, baseline, metrics, hypothesis, artifact_ids=artifacts)
        results.append(result)
        if result["decision"] == "adopt":
            current = result["variant"]
        if result["decision"] == "stop":
            break
    return results
