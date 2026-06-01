"""Local snapshot storage contracts."""

from __future__ import annotations

import json
import re
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


@dataclass(frozen=True)
class PublicDataArtifactManifest:
    artifact_id: str
    layer: str
    source: str
    endpoint: str
    symbol: str
    interval_or_period: str
    request_window: dict[str, Any]
    row_count: int
    path: str
    schema_version: str
    content_hash: str
    retention_note: str = ""
    checksum_url: str = ""
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


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.=-]+", "_", value).strip("_")


def write_public_raw_artifact(
    root: Path,
    *,
    source: str,
    endpoint: str,
    symbol: str,
    interval_or_period: str,
    request_window: dict[str, Any],
    rows: list[Any],
    retention_note: str = "",
    checksum_url: str = "",
    metadata: dict[str, Any] | None = None,
) -> PublicDataArtifactManifest:
    root.mkdir(parents=True, exist_ok=True)
    endpoint_name = _safe_name(endpoint.strip("/") or "root")
    stem = _safe_name(f"raw_{source}_{endpoint_name}_{symbol}_{interval_or_period}_{stable_hash(request_window)}")
    data_path = root / f"{stem}.json"
    payload = {
        "schema_version": "public-raw-v1",
        "source": source,
        "endpoint": endpoint,
        "symbol": symbol,
        "interval_or_period": interval_or_period,
        "request_window": request_window,
        "rows": rows,
        "retention_note": retention_note,
        "checksum_url": checksum_url,
        "metadata": metadata or {},
    }
    data_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    manifest = PublicDataArtifactManifest(
        artifact_id=stable_hash(payload),
        layer="raw",
        source=source,
        endpoint=endpoint,
        symbol=symbol,
        interval_or_period=interval_or_period,
        request_window=request_window,
        row_count=len(rows),
        path=str(data_path),
        schema_version="public-raw-v1",
        content_hash=stable_hash(payload),
        retention_note=retention_note,
        checksum_url=checksum_url,
        metadata=metadata or {},
    )
    (root / f"{stem}.manifest.json").write_text(json.dumps(asdict(manifest), indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def write_public_normalized_artifact(
    root: Path,
    *,
    source: str,
    endpoint: str,
    symbol: str,
    interval_or_period: str,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
    raw_artifact_ids: list[str],
    request_window: dict[str, Any] | None = None,
    retention_note: str = "",
    metadata: dict[str, Any] | None = None,
) -> PublicDataArtifactManifest:
    root.mkdir(parents=True, exist_ok=True)
    endpoint_name = _safe_name(endpoint.strip("/") or "root")
    stem = _safe_name(f"normalized_{source}_{endpoint_name}_{symbol}_{interval_or_period}_{stable_hash(raw_artifact_ids)}")
    csv_path = root / f"{stem}.csv"
    write_csv(csv_path, rows, fieldnames)
    payload_hash = stable_hash({"rows": rows, "fieldnames": fieldnames, "raw_artifact_ids": raw_artifact_ids})
    manifest = PublicDataArtifactManifest(
        artifact_id=payload_hash,
        layer="normalized",
        source=source,
        endpoint=endpoint,
        symbol=symbol,
        interval_or_period=interval_or_period,
        request_window=request_window or {},
        row_count=len(rows),
        path=str(csv_path),
        schema_version="public-normalized-v1",
        content_hash=payload_hash,
        retention_note=retention_note,
        metadata={**(metadata or {}), "raw_artifact_ids": raw_artifact_ids},
    )
    (root / f"{stem}.manifest.json").write_text(json.dumps(asdict(manifest), indent=2, sort_keys=True), encoding="utf-8")
    return manifest
