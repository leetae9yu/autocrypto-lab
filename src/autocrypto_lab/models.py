"""Dependency-light multi-factor model artifacts and signal scoring."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from autocrypto_lab.manifest import stable_hash


@dataclass(frozen=True)
class FactorModelArtifact:
    model_id: str
    model_type: str
    features: list[str]
    weights: dict[str, float]
    train_window: dict[str, Any]
    eval_window: dict[str, Any]
    input_hash: str
    metrics: dict[str, Any]
    signal_output_path: str = ""
    artifact_hash: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def deterministic_payload(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_type": self.model_type,
            "features": self.features,
            "weights": self.weights,
            "train_window": self.train_window,
            "eval_window": self.eval_window,
            "input_hash": self.input_hash,
            "metrics": self.metrics,
        }

    def with_outputs(self, signal_output_path: str) -> "FactorModelArtifact":
        payload = asdict(self)
        payload["signal_output_path"] = signal_output_path
        payload["artifact_hash"] = stable_hash(self.deterministic_payload())
        return FactorModelArtifact(**payload)


def _corr(rows: list[dict[str, Any]], feature: str, target: str) -> float:
    usable = [row for row in rows if row.get("label_available", True) and feature in row and target in row]
    if len(usable) < 2:
        return 0.0
    xs = [float(row[feature]) for row in usable]
    ys = [float(row[target]) for row in usable]
    xm = mean(xs)
    ym = mean(ys)
    cov = sum((x - xm) * (y - ym) for x, y in zip(xs, ys))
    xv = sum((x - xm) ** 2 for x in xs)
    yv = sum((y - ym) ** 2 for y in ys)
    if not xv or not yv:
        return 0.0
    return cov / (xv ** 0.5 * yv ** 0.5)


def fit_weighted_score_model(
    rows: list[dict[str, Any]],
    *,
    features: list[str],
    target: str = "forward_return",
    model_id: str = "weighted_score_v1",
) -> FactorModelArtifact:
    if not features:
        raise ValueError("at least one feature is required")
    weights = {feature: _corr(rows, feature, target) for feature in features}
    if not any(abs(weight) > 0 for weight in weights.values()):
        weights = {feature: 1.0 / len(features) for feature in features}
    train_rows = [row for row in rows if row.get("label_available", True)]
    timestamps = [row["timestamp"] for row in train_rows if "timestamp" in row]
    train_window = {"start": min(timestamps) if timestamps else None, "end": max(timestamps) if timestamps else None}
    metrics = {"feature_ic": weights, "n_train": len(train_rows)}
    artifact = FactorModelArtifact(
        model_id=model_id,
        model_type="weighted_score",
        features=list(features),
        weights=weights,
        train_window=train_window,
        eval_window=train_window,
        input_hash=stable_hash(rows),
        metrics=metrics,
    )
    return artifact.with_outputs("")


def score_model(rows: list[dict[str, Any]], model: FactorModelArtifact) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        score = sum(float(row.get(feature, 0.0)) * float(model.weights.get(feature, 0.0)) for feature in model.features)
        out.append({**row, "model_id": model.model_id, "signal_score": score})
    return out


def write_model_artifacts(root: Path, model: FactorModelArtifact, scored_rows: list[dict[str, Any]]) -> FactorModelArtifact:
    root.mkdir(parents=True, exist_ok=True)
    signal_path = root / f"{model.model_id}_signals.json"
    signal_path.write_text(json.dumps(scored_rows, indent=2, sort_keys=True, default=str), encoding="utf-8")
    model_with_path = model.with_outputs(str(signal_path))
    model_path = root / f"{model.model_id}.model.json"
    model_path.write_text(json.dumps(asdict(model_with_path), indent=2, sort_keys=True, default=str), encoding="utf-8")
    return model_with_path
