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
            else:
                enriched["forward_return"] = 0.0
                enriched["label_timestamp"] = row["timestamp"]
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


try:
    factor_registry.register("momentum", add_momentum)
except Exception:
    pass
