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


def run_dry_iteration(ledger_path: Path, config: dict[str, Any], baseline: dict[str, float], candidate: dict[str, float], hypothesis: str) -> dict[str, Any]:
    variant = propose_config_variant(config, hypothesis)
    decision = pareto_decision(candidate, baseline)
    entry = LedgerEntry(
        run_id=variant["run_id"],
        hypothesis=hypothesis,
        config_hash=stable_hash(variant),
        rationale="config-only dry-run variant evaluated with Pareto + diagnostics policy",
        metrics=candidate,
        decision=decision,
        evidence="dry-run metrics supplied by fixture test",
    )
    append_ledger(ledger_path, entry)
    return {"variant": variant, "decision": decision, "config_hash": entry.config_hash}
