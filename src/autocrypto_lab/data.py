"""Fixture/local market data loading and snapshot helpers."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NUMERIC_FIELDS = ("open", "high", "low", "close", "volume", "funding_rate", "open_interest", "spot_future_basis")


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_ohlcv_csv(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            row: dict[str, Any] = dict(raw)
            row["timestamp"] = parse_ts(str(raw["timestamp"]))
            row["symbol"] = str(raw["symbol"]).upper()
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
