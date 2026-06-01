"""JSONL ledger for reproducible autonomous research decisions."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

Decision = Literal["continue", "adopt", "defer", "stop"]


@dataclass(frozen=True)
class LedgerEntry:
    run_id: str
    hypothesis: str
    config_hash: str
    config_diff: dict[str, Any]
    config_snapshot: dict[str, Any]
    rationale: str
    metrics: dict[str, Any]
    decision: Decision
    evidence: str
    raw_data_snapshot_ids: list[str] = field(default_factory=list)
    normalized_data_snapshot_ids: list[str] = field(default_factory=list)
    feature_table_id: str = ""
    model_artifact_id: str = ""
    signal_artifact_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def validate(self) -> None:
        missing = [name for name in ("run_id", "hypothesis", "config_hash", "config_diff", "config_snapshot", "rationale", "decision", "evidence") if not getattr(self, name)]
        missing.extend(name for name in ("raw_data_snapshot_ids", "normalized_data_snapshot_ids", "feature_table_id", "model_artifact_id", "signal_artifact_id") if not getattr(self, name))
        if missing:
            raise ValueError(f"ledger entry missing required fields: {missing}")
        if self.decision not in ("continue", "adopt", "defer", "stop"):
            raise ValueError(f"invalid decision: {self.decision}")


def append_ledger(path: Path, entry: LedgerEntry) -> None:
    entry.validate()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(entry), sort_keys=True) + "\n")


def read_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
