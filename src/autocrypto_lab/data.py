"""Fixture/local market data loading and snapshot helpers."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NUMERIC_FIELDS = ("open", "high", "low", "close", "volume", "funding_rate", "open_interest", "spot_future_basis")
REQUIRED_FIELDS = ("timestamp", "symbol", *NUMERIC_FIELDS)


class DataValidationError(ValueError):
    """Raised when source data violates deterministic research input contracts."""


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_ohlcv_csv(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, datetime]] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            missing = [field for field in REQUIRED_FIELDS if not raw.get(field)]
            if missing:
                raise DataValidationError(f"missing required OHLCV fields: {missing}")
            row: dict[str, Any] = dict(raw)
            row["timestamp"] = parse_ts(str(raw["timestamp"]))
            row["symbol"] = str(raw["symbol"]).upper()
            key = (row["symbol"], row["timestamp"])
            if key in seen_keys:
                raise DataValidationError(f"duplicate symbol/timestamp row: {row['symbol']} {row['timestamp'].isoformat()}")
            seen_keys.add(key)
            for field in NUMERIC_FIELDS:
                row[field] = float(raw[field])
            rows.append(row)
    return sorted(rows, key=lambda item: (item["symbol"], item["timestamp"]))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            serializable = dict(row)
            if hasattr(serializable.get("timestamp"), "isoformat"):
                serializable["timestamp"] = serializable["timestamp"].isoformat().replace("+00:00", "Z")
            writer.writerow(serializable)
