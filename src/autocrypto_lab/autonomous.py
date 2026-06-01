"""Config-only autonomous research loop primitives."""

from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from autocrypto_lab.config import ALLOWED_CONFIG_KEYS, CPU_FRIENDLY_MODELS, load_config
from autocrypto_lab.ledger import LedgerEntry, append_ledger
from autocrypto_lab.manifest import stable_hash
from autocrypto_lab.pipeline import run_public_binance_pipeline

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
    metadata = candidate.get("metadata", {})
    if not isinstance(metadata, Mapping):
        raise ValueError("base_config metadata must be a mapping")
    candidate["metadata"] = dict(metadata)
    candidate["metadata"]["candidate_id"] = candidate_id
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
            "random_forest_depth3",
            "Random forest regressor tests nonlinear factor interactions while staying CPU-friendly.",
            {"model": "walk_forward_random_forest", "factors": base_factors, "model_params": {"n_estimators": 100, "max_depth": 3, "min_samples_leaf": 5, "random_state": 42, "n_jobs": 1}},
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
    templates.extend(
        [
            (
                "rebalance_8h_horizon",
                "Trade only every 8 hours on 8-hour forward labels to test whether lower turnover lets factor signal survive costs.",
                {"model": "walk_forward_sign_weight_score", "horizon_periods": 8, "factors": base_factors, "model_params": {"train_periods": 168, "test_periods": 24, "backtest_rebalance_periods": 8}},
            ),
            (
                "rebalance_24h_horizon",
                "Trade once per day on 24-hour forward labels to test a cost-aware low-turnover cross-sectional factor.",
                {"model": "walk_forward_equal_weight_score", "horizon_periods": 24, "factors": base_factors, "model_params": {"train_periods": 336, "test_periods": 24, "backtest_rebalance_periods": 24}},
            ),
            (
                "rf_rebalance_24h_horizon",
                "Random forest with daily rebalance tests nonlinear interactions under a low-turnover cost budget.",
                {"model": "walk_forward_random_forest", "horizon_periods": 24, "factors": base_factors, "model_params": {"train_periods": 336, "test_periods": 24, "backtest_rebalance_periods": 24, "n_estimators": 100, "max_depth": 4, "min_samples_leaf": 5, "random_state": 42, "n_jobs": 1}},
            ),
        ]
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


def _walk_forward_params(config: dict[str, Any], train_periods: int, test_periods: int, step_periods: int | None) -> dict[str, int | None]:
    params = dict(config.get("model_params", {}))
    return {
        "train_periods": int(params.get("train_periods", train_periods)),
        "test_periods": int(params.get("test_periods", test_periods)),
        "step_periods": int(params.get("step_periods", step_periods)) if params.get("step_periods", step_periods) is not None else None,
    }


def evaluate_candidate_configs(
    output_dir: Path,
    base_config: dict[str, Any],
    *,
    start: datetime,
    end: datetime,
    adapter: Any | None = None,
    max_candidates: int = 3,
    train_periods: int = 24,
    test_periods: int = 6,
    step_periods: int | None = None,
    ledger_path: Path | None = None,
) -> dict[str, Any]:
    """Evaluate generated candidates through the real public walk-forward pipeline."""
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates = generate_candidate_configs(base_config, max_candidates=max_candidates)
    evaluations: list[dict[str, Any]] = []
    ledger_path = ledger_path or output_dir / "agent_ledger.jsonl"
    for candidate in candidates:
        candidate_config = copy.deepcopy(candidate["config"])
        candidate_dir = output_dir / candidate["candidate_id"]
        wf_params = _walk_forward_params(candidate_config, train_periods, test_periods, step_periods)
        outputs = run_public_binance_pipeline(
            candidate_dir,
            candidate_config,
            start=start,
            end=end,
            adapter=adapter,
            train_periods=int(wf_params["train_periods"] or train_periods),
            test_periods=int(wf_params["test_periods"] or test_periods),
            step_periods=wf_params["step_periods"],
        )
        metrics = json.loads(outputs["metrics"].read_text(encoding="utf-8"))
        manifest = json.loads(outputs["manifest"].read_text(encoding="utf-8"))
        evaluations.append(
            {
                "candidate_id": candidate["candidate_id"],
                "hypothesis": candidate["hypothesis"],
                "run_id": candidate_config["run_id"],
                "config_hash": stable_hash(candidate_config),
                "config": candidate_config,
                "walk_forward": wf_params,
                "output_dir": str(candidate_dir),
                "artifact_paths": {name: str(path) for name, path in outputs.items()},
                "artifact_lineage": manifest["source_metadata"]["artifact_lineage"],
                "metrics": metrics,
            }
        )
    ranked = sorted(
        evaluations,
        key=lambda row: (
            float(row["metrics"].get("net_return_after_funding", row["metrics"].get("net_return", 0.0))),
            float(row["metrics"].get("max_drawdown", -1.0)),
            -float(row["metrics"].get("turnover", 999.0)),
        ),
        reverse=True,
    )
    pareto_ranks = {row["candidate_id"]: rank for rank, row in enumerate(ranked, start=1)}
    baseline_metrics = evaluations[0]["metrics"] if evaluations else {}
    for row in evaluations:
        decision = pareto_decision(row["metrics"], baseline_metrics)
        pareto_rank = pareto_ranks[row["candidate_id"]]
        if pareto_rank == 1 and decision == "continue":
            rationale = "top Pareto-ranked diagnostics are viable but not strictly better than the baseline candidate"
        elif decision == "adopt":
            rationale = "candidate improves return/drawdown diagnostics versus baseline within turnover guardrail"
        elif decision == "continue":
            rationale = "candidate has usable IC/quantile diagnostics but is not a clear Pareto improvement"
        else:
            rationale = "candidate lacks enough robust diagnostics for adoption"
        row["pareto_rank"] = pareto_rank
        row["decision"] = decision
        row["rationale"] = rationale
        lineage = row["artifact_lineage"]
        append_ledger(
            ledger_path,
            LedgerEntry(
                run_id=row["run_id"],
                parent_run_id=str(base_config.get("run_id", "run")),
                candidate_id=row["candidate_id"],
                hypothesis=row["hypothesis"],
                config_hash=row["config_hash"],
                config_diff=config_diff(base_config, row["config"]),
                config_snapshot=row["config"],
                rationale=rationale,
                metrics=row["metrics"],
                decision=decision,
                evidence="public walk-forward candidate evaluation",
                raw_data_snapshot_ids=list(lineage.get("raw_data_snapshot_ids", [])),
                normalized_data_snapshot_ids=list(lineage.get("normalized_data_snapshot_ids", [])),
                feature_table_id=str(lineage.get("feature_table_id", "")),
                model_artifact_id=str(lineage.get("model_artifact_id", "")),
                signal_artifact_id=str(lineage.get("signal_artifact_id", "")),
                model_family=str(row["config"].get("model", "")),
                hyperparameters=dict(row["config"].get("model_params", {})),
                pareto_rank=pareto_rank,
                report_path=row["artifact_paths"].get("report", ""),
                dashboard_path=row["artifact_paths"].get("dashboard", ""),
                manifest_path=row["artifact_paths"].get("manifest", ""),
            ),
        )
    summary = {
        "base_run_id": str(base_config.get("run_id", "run")),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "candidate_count": len(evaluations),
        "best_candidate_id": ranked[0]["candidate_id"] if ranked else "",
        "ledger_path": str(ledger_path),
        "evaluations": evaluations,
    }
    summary_path = output_dir / "candidate_evaluations.json"
    summary["summary_path"] = str(summary_path)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return summary


def _promoted_candidate(summary: dict[str, Any], promotion_policy: str) -> dict[str, Any] | None:
    evaluations = list(summary.get("evaluations", []))
    if not evaluations:
        return None
    ranked = sorted(evaluations, key=lambda row: int(row.get("pareto_rank", 999)))
    if promotion_policy == "adopt_only":
        return next((row for row in ranked if row.get("decision") == "adopt"), None)
    if promotion_policy == "pareto_best":
        return ranked[0]
    raise ValueError(f"unknown promotion_policy: {promotion_policy}")


def _next_base_config(original_run_id: str, iteration: int, selected: dict[str, Any]) -> dict[str, Any]:
    next_config = copy.deepcopy(selected["config"])
    next_config["run_id"] = f"{original_run_id}_iteration_{iteration + 1:03d}_base"
    metadata = dict(next_config.get("metadata", {}))
    metadata.update(
        {
            "promoted_from_candidate_id": selected["candidate_id"],
            "promoted_from_run_id": selected["run_id"],
            "promoted_from_iteration": iteration,
            "promotion_decision": selected.get("decision", ""),
            "promotion_pareto_rank": selected.get("pareto_rank", 0),
            "promotion_rationale": selected.get("rationale", ""),
        }
    )
    next_config["metadata"] = metadata
    load_config(next_config)
    return next_config


def run_iterative_agent_loop(
    output_dir: Path,
    base_config: dict[str, Any],
    *,
    start: datetime,
    end: datetime,
    adapter: Any | None = None,
    iterations: int = 1,
    max_candidates: int = 3,
    train_periods: int = 24,
    test_periods: int = 6,
    step_periods: int | None = None,
    promotion_policy: str = "pareto_best",
) -> dict[str, Any]:
    """Run the real feedback loop: evaluate, promote config, then evaluate again."""
    if iterations < 1:
        raise ValueError("iterations must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    original_run_id = str(base_config.get("run_id", "run"))
    current_config = copy.deepcopy(base_config)
    ledger_path = output_dir / "agent_ledger.jsonl"
    iteration_summaries: list[dict[str, Any]] = []
    for iteration in range(1, iterations + 1):
        iteration_dir = output_dir / f"iteration_{iteration:03d}"
        summary = evaluate_candidate_configs(
            iteration_dir,
            current_config,
            start=start,
            end=end,
            adapter=adapter,
            max_candidates=max_candidates,
            train_periods=train_periods,
            test_periods=test_periods,
            step_periods=step_periods,
            ledger_path=ledger_path,
        )
        selected = _promoted_candidate(summary, promotion_policy)
        summary["iteration"] = iteration
        summary["base_config_hash"] = stable_hash(current_config)
        summary["promotion_policy"] = promotion_policy
        summary["promoted_candidate_id"] = selected["candidate_id"] if selected else ""
        summary["promoted_decision"] = selected.get("decision", "") if selected else ""
        summary["promoted_pareto_rank"] = selected.get("pareto_rank", 0) if selected else 0
        if selected and iteration < iterations:
            current_config = _next_base_config(original_run_id, iteration, selected)
            summary["next_base_config"] = current_config
        Path(summary["summary_path"]).write_text(json.dumps(summary, indent=2, sort_keys=True, default=str), encoding="utf-8")
        iteration_summaries.append(
            {
                "iteration": iteration,
                "summary_path": summary["summary_path"],
                "base_run_id": summary["base_run_id"],
                "best_candidate_id": summary["best_candidate_id"],
                "promoted_candidate_id": summary["promoted_candidate_id"],
                "promoted_decision": summary["promoted_decision"],
                "candidate_count": summary["candidate_count"],
            }
        )
        if selected is None:
            break
    aggregate = {
        "base_run_id": original_run_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "iterations_requested": iterations,
        "iterations_completed": len(iteration_summaries),
        "max_candidates": max_candidates,
        "promotion_policy": promotion_policy,
        "ledger_path": str(ledger_path),
        "iteration_summaries": iteration_summaries,
        "final_base_config": current_config,
    }
    summary_path = output_dir / "agent_loop_summary.json"
    aggregate["summary_path"] = str(summary_path)
    summary_path.write_text(json.dumps(aggregate, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return aggregate


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
