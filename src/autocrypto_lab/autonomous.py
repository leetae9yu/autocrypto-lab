"""Config-only autonomous research loop primitives."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from autocrypto_lab.config import ALLOWED_CONFIG_KEYS, CPU_FRIENDLY_MODELS, load_config
from autocrypto_lab.ledger import LedgerEntry, append_ledger
from autocrypto_lab.manifest import stable_hash

CONFIG_MUTATION_KEYS = set(ALLOWED_CONFIG_KEYS)


def _factor_name(factor: Any) -> str:
    if isinstance(factor, str):
        return factor
    if isinstance(factor, dict):
        return str(factor.get("name", ""))
    return ""


def _with_candidate_defaults(base_config: dict[str, Any], candidate_id: str, hypothesis: str) -> dict[str, Any]:
    candidate = copy.deepcopy(base_config)
    candidate["run_id"] = f"{base_config.get('run_id', 'run')}_{candidate_id}"
    candidate["public_only"] = True
    candidate["allow_private_read"] = False
    candidate["allow_trading"] = False
    candidate.setdefault("metadata", {})["candidate_id"] = candidate_id
    candidate["metadata"]["hypothesis"] = hypothesis
    return candidate


def generate_candidate_configs(base_config: dict[str, Any], max_candidates: int = 6) -> list[dict[str, Any]]:
    """Generate deterministic, config-only CPU-friendly research candidates.

    The generator mutates only experiment config fields, validates every candidate
    through the public-only config contract, and never proposes source-code edits.
    """
    if max_candidates < 1:
        return []
    unknown_base_keys = sorted(set(base_config) - CONFIG_MUTATION_KEYS)
    if unknown_base_keys:
        raise ValueError(f"base_config has unknown config keys: {unknown_base_keys}")

    base_factors = list(copy.deepcopy(base_config.get("factors", ["momentum"])))
    base_factor_names = {_factor_name(factor) for factor in base_factors}
    templates: list[tuple[str, str, dict[str, Any]]] = [
        (
            "weighted_score_baseline",
            "Correlation-weighted walk-forward score tests whether existing factors still explain next-period returns.",
            {"model": "walk_forward_weighted_score", "factors": base_factors},
        ),
        (
            "equal_weight_robustness",
            "Equal-weight score checks whether avoiding IC overfit improves robustness.",
            {"model": "walk_forward_equal_weight_score", "factors": base_factors},
        ),
        (
            "sign_weight_directional",
            "Sign-weight score keeps only directional IC information to reduce parameter sensitivity.",
            {"model": "walk_forward_sign_weight_score", "factors": base_factors},
        ),
        (
            "short_train_window",
            "Shorter walk-forward train window tests faster regime adaptation with the same factor set.",
            {"model": "walk_forward_weighted_score", "factors": base_factors, "model_params": {"train_periods": 24, "test_periods": 6}},
        ),
        (
            "long_train_window",
            "Longer walk-forward train window tests smoother parameter estimates across regimes.",
            {"model": "walk_forward_weighted_score", "factors": base_factors, "model_params": {"train_periods": 72, "test_periods": 12}},
        ),
    ]
    if "reversal" not in base_factor_names:
        templates.append(
            (
                "add_reversal_factor",
                "Add reversal to test whether short-horizon mean reversion improves the factor stack.",
                {"model": "walk_forward_sign_weight_score", "factors": [*base_factors, "reversal"]},
            )
        )
    if "volatility" not in base_factor_names:
        templates.append(
            (
                "add_volatility_factor",
                "Add volatility to test whether risk-state information improves drawdown diagnostics.",
                {"model": "walk_forward_equal_weight_score", "factors": [*base_factors, "volatility"]},
            )
        )
    templates.append(
        (
            "momentum_lookback_3",
            "Use a shorter momentum lookback to test whether recent trend information dominates.",
            {"model": "walk_forward_weighted_score", "factors": [{"name": "momentum", "params": {"lookback_periods": 3}}]},
        )
    )

    candidates: list[dict[str, Any]] = []
    for idx, (slug, hypothesis, overrides) in enumerate(templates, start=1):
        if len(candidates) >= max_candidates:
            break
        candidate_id = f"candidate_{idx:03d}_{slug}"
        config = _with_candidate_defaults(base_config, candidate_id, hypothesis)
        config.update(copy.deepcopy(overrides))
        if config["model"] not in CPU_FRIENDLY_MODELS:
            raise ValueError(f"candidate {candidate_id} selected non-CPU model: {config['model']}")
        unknown_keys = sorted(set(config) - CONFIG_MUTATION_KEYS)
        if unknown_keys:
            raise ValueError(f"candidate {candidate_id} has unknown config keys: {unknown_keys}")
        load_config(config)
        candidates.append({"candidate_id": candidate_id, "hypothesis": hypothesis, "config": config})
    return candidates


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
    artifact_ids: dict[str, Any],
) -> dict[str, Any]:
    variant = propose_config_variant(config, hypothesis)
    decision = pareto_decision(candidate, baseline)
    artifacts = artifact_ids
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
