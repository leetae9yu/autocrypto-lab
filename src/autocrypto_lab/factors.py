"""Core factor computations for the walking skeleton."""

from __future__ import annotations

from collections import defaultdict
from statistics import pstdev
from typing import Any

from autocrypto_lab.registry import factor_registry


def add_momentum(rows: list[dict[str, Any]], lookback: int = 1) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["symbol"]].append(row)
    out: list[dict[str, Any]] = []
    for symbol_rows in grouped.values():
        symbol_rows = sorted(symbol_rows, key=lambda r: r["timestamp"])
        for idx, row in enumerate(symbol_rows):
            enriched = dict(row)
            if idx >= lookback:
                prev = symbol_rows[idx - lookback]["close"]
                enriched["momentum"] = row["close"] / prev - 1.0
            else:
                enriched["momentum"] = 0.0
            out.append(enriched)
    return sorted(out, key=lambda item: (item["symbol"], item["timestamp"]))


def add_forward_returns(rows: list[dict[str, Any]], horizon: int = 1) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["symbol"]].append(row)
    out: list[dict[str, Any]] = []
    for symbol_rows in grouped.values():
        symbol_rows = sorted(symbol_rows, key=lambda r: r["timestamp"])
        for idx, row in enumerate(symbol_rows):
            enriched = dict(row)
            if idx + horizon < len(symbol_rows):
                fut = symbol_rows[idx + horizon]["close"]
                enriched["forward_return"] = fut / row["close"] - 1.0
                enriched["label_timestamp"] = symbol_rows[idx + horizon]["timestamp"]
                enriched["label_available"] = True
            else:
                enriched["forward_return"] = 0.0
                enriched["label_timestamp"] = row["timestamp"]
                enriched["label_available"] = False
            out.append(enriched)
    return sorted(out, key=lambda item: (item["symbol"], item["timestamp"]))


def add_volatility(rows: list[dict[str, Any]], lookback: int = 3) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["symbol"]].append(row)
    out: list[dict[str, Any]] = []
    for symbol_rows in grouped.values():
        symbol_rows = sorted(symbol_rows, key=lambda r: r["timestamp"])
        rets = [0.0]
        for prev, cur in zip(symbol_rows, symbol_rows[1:]):
            rets.append(cur["close"] / prev["close"] - 1.0)
        for idx, row in enumerate(symbol_rows):
            enriched = dict(row)
            window = rets[max(0, idx - lookback + 1): idx + 1]
            enriched["volatility"] = pstdev(window) if len(window) > 1 else 0.0
            out.append(enriched)
    return sorted(out, key=lambda item: (item["symbol"], item["timestamp"]))


if "momentum" not in factor_registry.names():
    factor_registry.register("momentum", add_momentum)


def add_reversal(rows: list[dict[str, Any]], lookback: int = 1) -> list[dict[str, Any]]:
    return [{**row, "reversal": -float(row.get("momentum", 0.0))} for row in add_momentum(rows, lookback=lookback)]


def add_flow(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        enriched = dict(row)
        enriched["flow"] = float(row.get("volume", 0.0)) * float(row.get("close", 0.0))
        out.append(enriched)
    return out


def add_derivatives_pressure(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        enriched = dict(row)
        enriched["derivatives_pressure"] = float(row.get("funding_rate", 0.0)) + float(row.get("spot_future_basis", 0.0)) / 10_000.0
        out.append(enriched)
    return out


def _normalize_lookback_params(params: dict[str, Any]) -> dict[str, Any]:
    """Accept config-facing lookback aliases while calling fixed factor functions."""
    normalized = dict(params)
    if "lookback_periods" in normalized:
        if "lookback" in normalized and normalized["lookback"] != normalized["lookback_periods"]:
            raise ValueError("factor params cannot set conflicting lookback and lookback_periods")
        normalized["lookback"] = normalized.pop("lookback_periods")
    return normalized


def apply_factor_dsl(rows: list[dict[str, Any]], specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply declarative factor specs without allowing code mutation."""
    out = rows
    for spec in specs:
        name = spec["name"]
        params = dict(spec.get("params", {}))
        if name == "momentum":
            out = add_momentum(out, **_normalize_lookback_params(params))
        elif name == "reversal":
            out = add_reversal(out, **_normalize_lookback_params(params))
        elif name == "volatility":
            out = add_volatility(out, **_normalize_lookback_params(params))
        elif name == "flow":
            out = add_flow(out)
        elif name == "derivatives_pressure":
            out = add_derivatives_pressure(out)
        else:
            raise ValueError(f"unknown factor spec: {name}")
    return out


def _latest_known(rows: list[dict[str, Any]], symbol: str, timestamp: Any) -> dict[str, Any]:
    def known_time(row: dict[str, Any]) -> Any:
        return row.get("known_at") or row.get("timestamp")

    candidates = [
        row
        for row in rows
        if row.get("symbol") == symbol
        and row.get("timestamp") <= timestamp
        and known_time(row) <= timestamp
    ]
    if not candidates:
        return {}
    return max(candidates, key=known_time)


def build_public_futures_feature_table(
    klines: list[dict[str, Any]],
    funding: list[dict[str, Any]],
    open_interest: list[dict[str, Any]],
    basis: list[dict[str, Any]],
    *,
    horizon: int = 1,
    factor_specs: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Join public futures sources by known-at timestamp and add model-ready factors."""
    base = []
    for row in sorted(klines, key=lambda item: (item["symbol"], item["timestamp"])):
        symbol = row["symbol"]
        timestamp = row["timestamp"]
        f = _latest_known(funding, symbol, timestamp)
        oi = _latest_known(open_interest, symbol, timestamp)
        b = _latest_known(basis, symbol, timestamp)
        enriched = dict(row)
        enriched["known_at"] = timestamp
        enriched["funding_rate"] = float(f.get("funding_rate", 0.0))
        enriched["open_interest"] = float(oi.get("open_interest", 0.0))
        enriched["spot_future_basis"] = float(b.get("spot_future_basis", b.get("basis", 0.0)))
        enriched["source_known_at"] = {
            "kline": timestamp,
            "funding": f.get("known_at", f.get("timestamp")),
            "open_interest": oi.get("known_at", oi.get("timestamp")),
            "basis": b.get("known_at", b.get("timestamp")),
        }
        base.append(enriched)
    featured = apply_factor_dsl(base, factor_specs or [{"name": "momentum"}, {"name": "volatility"}, {"name": "derivatives_pressure"}])
    return add_forward_returns(featured, horizon=horizon)


for _name, _fn in {
    "reversal": add_reversal,
    "volatility": add_volatility,
    "flow": add_flow,
    "derivatives_pressure": add_derivatives_pressure,
}.items():
    if _name not in factor_registry.names():
        factor_registry.register(_name, _fn)
