"""Small deterministic cost-aware backtest diagnostics."""

from __future__ import annotations

from statistics import mean, pstdev
from typing import Any


def max_drawdown(returns: list[float]) -> float:
    equity = 1.0
    peak = 1.0
    worst = 0.0
    for ret in returns:
        equity *= 1.0 + ret
        peak = max(peak, equity)
        worst = min(worst, equity / peak - 1.0)
    return worst


def is_labeled(row: dict[str, Any]) -> bool:
    return bool(row.get("label_available", True)) and row.get("label_timestamp", row["timestamp"]) > row["timestamp"]


def run_long_short(rows: list[dict[str, Any]], factor: str, fee_bps: float = 5.0, slippage_bps: float = 2.0) -> dict[str, Any]:
    usable = [row for row in rows if "forward_return" in row and factor in row and is_labeled(row)]
    by_timestamp: dict[Any, list[dict[str, Any]]] = {}
    for row in usable:
        by_timestamp.setdefault(row["timestamp"], []).append(row)
    gross_returns: list[float] = []
    net_returns: list[float] = []
    long_symbols: list[str] = []
    short_symbols: list[str] = []
    per_period_cost = 2.0 * (fee_bps + slippage_bps) / 10_000.0
    for timestamp in sorted(by_timestamp):
        cohort = by_timestamp[timestamp]
        if len(cohort) < 2:
            continue
        ranked = sorted(cohort, key=lambda row: row[factor])
        short = ranked[0]
        long = ranked[-1]
        gross = float(long["forward_return"]) - float(short["forward_return"])
        gross_returns.append(gross)
        net_returns.append(gross - per_period_cost)
        long_symbols.append(long["symbol"])
        short_symbols.append(short["symbol"])
    if not net_returns:
        return {"periods": 0, "gross_return": 0.0, "net_return": 0.0, "volatility": 0.0, "max_drawdown": 0.0, "turnover": 0.0, "long_symbol": "n/a", "short_symbol": "n/a", "cost": 0.0}
    cost = per_period_cost * len(net_returns)
    return {
        "periods": len(net_returns),
        "gross_return": sum(gross_returns),
        "net_return": sum(net_returns),
        "volatility": pstdev(net_returns) if len(net_returns) > 1 else 0.0,
        "max_drawdown": max_drawdown(net_returns),
        "turnover": 2.0 * len(net_returns),
        "long_symbol": ",".join(long_symbols),
        "short_symbol": ",".join(short_symbols),
        "cost": cost,
    }


def information_coefficient(rows: list[dict[str, Any]], factor: str) -> float:
    usable = [row for row in rows if factor in row and "forward_return" in row and is_labeled(row)]
    if len(usable) < 2:
        return 0.0
    f_mean = mean([row[factor] for row in usable])
    r_mean = mean([row["forward_return"] for row in usable])
    cov = sum((row[factor] - f_mean) * (row["forward_return"] - r_mean) for row in usable)
    f_var = sum((row[factor] - f_mean) ** 2 for row in usable)
    r_var = sum((row["forward_return"] - r_mean) ** 2 for row in usable)
    if not f_var or not r_var:
        return 0.0
    return cov / (f_var ** 0.5 * r_var ** 0.5)


def quantile_returns(rows: list[dict[str, Any]], factor: str, buckets: int = 3) -> dict[str, float]:
    usable = sorted([row for row in rows if factor in row and "forward_return" in row and is_labeled(row)], key=lambda row: row[factor])
    if not usable:
        return {}
    out: dict[str, float] = {}
    for idx, row in enumerate(usable):
        bucket = min(buckets, int(idx * buckets / len(usable)) + 1)
        out.setdefault(f"q{bucket}", 0.0)
        out[f"q{bucket}"] += float(row["forward_return"])
    counts = {key: 0 for key in out}
    for idx, _ in enumerate(usable):
        bucket = min(buckets, int(idx * buckets / len(usable)) + 1)
        counts[f"q{bucket}"] += 1
    return {key: value / counts[key] for key, value in out.items()}


def research_diagnostics(rows: list[dict[str, Any]], factor: str, fee_bps: float = 5.0, slippage_bps: float = 2.0, funding_cost: float = 0.0) -> dict[str, Any]:
    ls = run_long_short(rows, factor=factor, fee_bps=fee_bps, slippage_bps=slippage_bps)
    ls["funding_cost"] = funding_cost
    ls["net_return_after_funding"] = float(ls["net_return"]) - funding_cost
    ls["ic"] = information_coefficient(rows, factor)
    ls["quantile_returns"] = quantile_returns(rows, factor)
    ls["robustness_flags"] = {
        "cost_survives": ls["net_return_after_funding"] > 0,
        "has_quantiles": bool(ls["quantile_returns"]),
        "has_ic": ls["ic"] != 0.0,
    }
    return ls
