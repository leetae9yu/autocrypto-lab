"""Local snapshot storage contracts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autocrypto_lab.data import write_csv
from autocrypto_lab.manifest import stable_hash


@dataclass(frozen=True)
class SnapshotManifest:
    source: str
    symbol: str
    interval: str
    row_count: int
    path: str
    config_hash: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


def write_snapshot(root: Path, source: str, symbol: str, interval: str, rows: list[dict], metadata: dict[str, Any] | None = None) -> SnapshotManifest:
    root.mkdir(parents=True, exist_ok=True)
    csv_path = root / f"{source}_{symbol}_{interval}.csv"
    fieldnames = ["timestamp", "symbol", "open", "high", "low", "close", "volume", "funding_rate", "open_interest", "spot_future_basis"]
    write_csv(csv_path, rows, fieldnames)
    manifest = SnapshotManifest(
        source=source,
        symbol=symbol,
        interval=interval,
        row_count=len(rows),
        path=str(csv_path),
        config_hash=stable_hash({"source": source, "symbol": symbol, "interval": interval, "rows": len(rows)}),
        metadata=metadata or {},
    )
    (root / f"{source}_{symbol}_{interval}.manifest.json").write_text(json.dumps(asdict(manifest), indent=2, sort_keys=True), encoding="utf-8")
    return manifest
