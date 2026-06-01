"""Dependency-light multi-factor model artifacts and signal scoring."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from autocrypto_lab.manifest import stable_hash

WEIGHT_MODE_BY_MODEL_FAMILY = {
    "walk_forward_weighted_score": "correlation",
    "walk_forward_equal_weight_score": "equal",
    "walk_forward_sign_weight_score": "sign",
}
STATIC_WEIGHT_MODES = ("correlation", "equal", "sign")
RANDOM_FOREST_MODEL_FAMILY = "walk_forward_random_forest"


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
    weight_mode: str = "correlation",
    model_type: str = "weighted_score",
) -> FactorModelArtifact:
    if not features:
        raise ValueError("at least one feature is required")
    if weight_mode not in STATIC_WEIGHT_MODES:
        raise ValueError(f"unknown CPU-friendly weight_mode: {weight_mode}")
    feature_ic = {feature: _corr(rows, feature, target) for feature in features}
    if weight_mode == "equal":
        weights = {feature: 1.0 / len(features) for feature in features}
    elif weight_mode == "sign":
        non_zero = [feature for feature, corr in feature_ic.items() if abs(corr) > 0]
        if non_zero:
            weights = {
                feature: ((1.0 if feature_ic[feature] > 0 else -1.0) / len(non_zero) if feature in non_zero else 0.0)
                for feature in features
            }
        else:
            weights = {feature: 1.0 / len(features) for feature in features}
    else:
        weights = dict(feature_ic)
        if not any(abs(weight) > 0 for weight in weights.values()):
            weights = {feature: 1.0 / len(features) for feature in features}
    train_rows = [row for row in rows if row.get("label_available", True)]
    timestamps = [row["timestamp"] for row in train_rows if "timestamp" in row]
    train_window = {"start": min(timestamps) if timestamps else None, "end": max(timestamps) if timestamps else None}
    metrics = {"feature_ic": feature_ic, "weight_mode": weight_mode, "n_train": len(train_rows)}
    artifact = FactorModelArtifact(
        model_id=model_id,
        model_type=model_type,
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


def fit_walk_forward_weighted_score_model(
    rows: list[dict[str, Any]],
    *,
    features: list[str],
    target: str = "forward_return",
    model_id: str = "walk_forward_weighted_score_v1",
    train_periods: int = 24,
    test_periods: int = 6,
    step_periods: int | None = None,
    model_family: str = "walk_forward_weighted_score",
) -> tuple[FactorModelArtifact, list[dict[str, Any]]]:
    """Fit factor weights on rolling train windows and score only later test windows."""
    if model_family not in WEIGHT_MODE_BY_MODEL_FAMILY:
        raise ValueError(f"unknown CPU-friendly walk-forward model family: {model_family}")
    weight_mode = WEIGHT_MODE_BY_MODEL_FAMILY[model_family]
    if train_periods < 1 or test_periods < 1:
        raise ValueError("walk-forward train_periods and test_periods must be positive")
    step = step_periods or test_periods
    if step < 1:
        raise ValueError("walk-forward step_periods must be positive")
    timestamps = sorted({row["timestamp"] for row in rows})
    fold_start = 0
    fold_idx = 0
    scored_rows: list[dict[str, Any]] = []
    folds: list[dict[str, Any]] = []
    fold_weights: list[dict[str, float]] = []
    while fold_start + train_periods + test_periods <= len(timestamps):
        train_ts = timestamps[fold_start: fold_start + train_periods]
        test_ts = timestamps[fold_start + train_periods: fold_start + train_periods + test_periods]
        train_end = train_ts[-1]
        train_set = set(train_ts)
        test_set = set(test_ts)
        train_rows = [
            row
            for row in rows
            if row["timestamp"] in train_set
            and row.get("label_available", True)
            and row.get("label_timestamp", row["timestamp"]) <= train_end
        ]
        test_rows = [row for row in rows if row["timestamp"] in test_set]
        if train_rows and test_rows:
            fold_model = fit_weighted_score_model(
                train_rows,
                features=features,
                target=target,
                model_id=f"{model_id}_fold_{fold_idx}",
                weight_mode=weight_mode,
                model_type=model_family,
            )
            fold_weights.append(fold_model.weights)
            for scored in score_model(test_rows, fold_model):
                scored_rows.append(
                    {
                        **scored,
                        "model_id": model_id,
                        "walk_forward_fold": fold_idx,
                        "train_start": train_ts[0],
                        "train_end": train_ts[-1],
                        "test_start": test_ts[0],
                        "test_end": test_ts[-1],
                    }
                )
            folds.append(
                {
                    "fold": fold_idx,
                    "train_start": train_ts[0],
                    "train_end": train_ts[-1],
                    "test_start": test_ts[0],
                    "test_end": test_ts[-1],
                    "n_train": len(train_rows),
                    "n_test": len(test_rows),
                    "weights": fold_model.weights,
                }
            )
            fold_idx += 1
        fold_start += step
    if not scored_rows:
        raise ValueError("walk-forward configuration produced no scored out-of-sample rows")
    average_weights = {
        feature: mean([weights.get(feature, 0.0) for weights in fold_weights])
        for feature in features
    }
    train_window = {"start": folds[0]["train_start"], "end": folds[-1]["train_end"]}
    eval_window = {"start": folds[0]["test_start"], "end": folds[-1]["test_end"]}
    artifact = FactorModelArtifact(
        model_id=model_id,
        model_type=model_family,
        features=list(features),
        weights=average_weights,
        train_window=train_window,
        eval_window=eval_window,
        input_hash=stable_hash({"rows": rows, "features": features, "model_family": model_family, "train_periods": train_periods, "test_periods": test_periods, "step_periods": step}),
        metrics={
            "walk_forward": True,
            "model_family": model_family,
            "weight_mode": weight_mode,
            "train_periods": train_periods,
            "test_periods": test_periods,
            "step_periods": step,
            "folds": folds,
            "n_scored": len(scored_rows),
        },
    )
    return artifact.with_outputs(""), sorted(scored_rows, key=lambda row: (row["timestamp"], row["symbol"]))


def fit_walk_forward_random_forest_model(
    rows: list[dict[str, Any]],
    *,
    features: list[str],
    target: str = "forward_return",
    model_id: str = "walk_forward_random_forest_v1",
    train_periods: int = 24,
    test_periods: int = 6,
    step_periods: int | None = None,
    n_estimators: int = 100,
    max_depth: int | None = 3,
    min_samples_leaf: int = 5,
    random_state: int = 42,
    n_jobs: int = 1,
) -> tuple[FactorModelArtifact, list[dict[str, Any]]]:
    """Fit a CPU-friendly random forest regressor on rolling train windows."""
    if not features:
        raise ValueError("at least one feature is required")
    if train_periods < 1 or test_periods < 1:
        raise ValueError("walk-forward train_periods and test_periods must be positive")
    if n_estimators < 1:
        raise ValueError("random forest n_estimators must be positive")
    if min_samples_leaf < 1:
        raise ValueError("random forest min_samples_leaf must be positive")
    from sklearn.ensemble import RandomForestRegressor

    step = step_periods or test_periods
    if step < 1:
        raise ValueError("walk-forward step_periods must be positive")
    timestamps = sorted({row["timestamp"] for row in rows})
    fold_start = 0
    fold_idx = 0
    scored_rows: list[dict[str, Any]] = []
    folds: list[dict[str, Any]] = []
    fold_importances: list[dict[str, float]] = []
    while fold_start + train_periods + test_periods <= len(timestamps):
        train_ts = timestamps[fold_start: fold_start + train_periods]
        test_ts = timestamps[fold_start + train_periods: fold_start + train_periods + test_periods]
        train_end = train_ts[-1]
        train_set = set(train_ts)
        test_set = set(test_ts)
        train_rows = [
            row
            for row in rows
            if row["timestamp"] in train_set
            and row.get("label_available", True)
            and row.get("label_timestamp", row["timestamp"]) <= train_end
        ]
        test_rows = [row for row in rows if row["timestamp"] in test_set]
        if train_rows and test_rows:
            x_train = [[float(row.get(feature, 0.0)) for feature in features] for row in train_rows]
            y_train = [float(row.get(target, 0.0)) for row in train_rows]
            x_test = [[float(row.get(feature, 0.0)) for feature in features] for row in test_rows]
            regressor = RandomForestRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                min_samples_leaf=min_samples_leaf,
                random_state=random_state + fold_idx,
                n_jobs=n_jobs,
            )
            regressor.fit(x_train, y_train)
            predictions = regressor.predict(x_test)
            importances = {feature: float(value) for feature, value in zip(features, regressor.feature_importances_)}
            fold_importances.append(importances)
            for row, prediction in zip(test_rows, predictions):
                scored_rows.append(
                    {
                        **row,
                        "model_id": model_id,
                        "signal_score": float(prediction),
                        "walk_forward_fold": fold_idx,
                        "train_start": train_ts[0],
                        "train_end": train_ts[-1],
                        "test_start": test_ts[0],
                        "test_end": test_ts[-1],
                    }
                )
            folds.append(
                {
                    "fold": fold_idx,
                    "train_start": train_ts[0],
                    "train_end": train_ts[-1],
                    "test_start": test_ts[0],
                    "test_end": test_ts[-1],
                    "n_train": len(train_rows),
                    "n_test": len(test_rows),
                    "feature_importances": importances,
                }
            )
            fold_idx += 1
        fold_start += step
    if not scored_rows:
        raise ValueError("walk-forward random forest configuration produced no scored out-of-sample rows")
    average_importances = {
        feature: mean([importance.get(feature, 0.0) for importance in fold_importances])
        for feature in features
    }
    train_window = {"start": folds[0]["train_start"], "end": folds[-1]["train_end"]}
    eval_window = {"start": folds[0]["test_start"], "end": folds[-1]["test_end"]}
    artifact = FactorModelArtifact(
        model_id=model_id,
        model_type=RANDOM_FOREST_MODEL_FAMILY,
        features=list(features),
        weights=average_importances,
        train_window=train_window,
        eval_window=eval_window,
        input_hash=stable_hash(
            {
                "rows": rows,
                "features": features,
                "model_family": RANDOM_FOREST_MODEL_FAMILY,
                "train_periods": train_periods,
                "test_periods": test_periods,
                "step_periods": step,
                "n_estimators": n_estimators,
                "max_depth": max_depth,
                "min_samples_leaf": min_samples_leaf,
                "random_state": random_state,
            }
        ),
        metrics={
            "walk_forward": True,
            "model_family": RANDOM_FOREST_MODEL_FAMILY,
            "estimator": "sklearn.ensemble.RandomForestRegressor",
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "min_samples_leaf": min_samples_leaf,
            "random_state": random_state,
            "n_jobs": n_jobs,
            "train_periods": train_periods,
            "test_periods": test_periods,
            "step_periods": step,
            "folds": folds,
            "n_scored": len(scored_rows),
        },
    )
    return artifact.with_outputs(""), sorted(scored_rows, key=lambda row: (row["timestamp"], row["symbol"]))


def write_model_artifacts(root: Path, model: FactorModelArtifact, scored_rows: list[dict[str, Any]]) -> FactorModelArtifact:
    root.mkdir(parents=True, exist_ok=True)
    signal_path = root / f"{model.model_id}_signals.json"
    signal_path.write_text(json.dumps(scored_rows, indent=2, sort_keys=True, default=str), encoding="utf-8")
    model_with_path = model.with_outputs(str(signal_path))
    model_path = root / f"{model.model_id}.model.json"
    model_path.write_text(json.dumps(asdict(model_with_path), indent=2, sort_keys=True, default=str), encoding="utf-8")
    return model_with_path
