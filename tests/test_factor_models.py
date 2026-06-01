from datetime import datetime, timezone
from pathlib import Path

from autocrypto_lab.factors import build_public_futures_feature_table
from autocrypto_lab.models import fit_walk_forward_random_forest_model, fit_walk_forward_weighted_score_model, fit_weighted_score_model, score_model, write_model_artifacts


def ts(hour: int):
    return datetime(2024, 1, 10, hour, tzinfo=timezone.utc)


def feature_rows():
    klines = [
        {"timestamp": ts(0), "symbol": "BTCUSDT", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 10.0},
        {"timestamp": ts(1), "symbol": "BTCUSDT", "open": 100.0, "high": 104.0, "low": 100.0, "close": 103.0, "volume": 14.0},
        {"timestamp": ts(2), "symbol": "BTCUSDT", "open": 103.0, "high": 105.0, "low": 102.0, "close": 104.0, "volume": 11.0},
        {"timestamp": ts(0), "symbol": "ETHUSDT", "open": 20.0, "high": 21.0, "low": 19.0, "close": 20.0, "volume": 6.0},
        {"timestamp": ts(1), "symbol": "ETHUSDT", "open": 20.0, "high": 20.5, "low": 19.0, "close": 19.5, "volume": 8.0},
        {"timestamp": ts(2), "symbol": "ETHUSDT", "open": 19.5, "high": 20.5, "low": 19.0, "close": 20.0, "volume": 9.0},
    ]
    funding = [{"timestamp": ts(0), "symbol": "BTCUSDT", "funding_rate": 0.0001}, {"timestamp": ts(0), "symbol": "ETHUSDT", "funding_rate": -0.0001}]
    oi = [{"timestamp": ts(0), "symbol": "BTCUSDT", "open_interest": 1000.0}, {"timestamp": ts(0), "symbol": "ETHUSDT", "open_interest": 500.0}]
    basis = [{"timestamp": ts(0), "symbol": "BTCUSDT", "spot_future_basis": 12.0}, {"timestamp": ts(0), "symbol": "ETHUSDT", "spot_future_basis": -2.0}]
    return build_public_futures_feature_table(klines, funding, oi, basis)


def test_weighted_score_model_produces_artifact_and_scores():
    rows = feature_rows()
    model = fit_weighted_score_model(rows, features=["momentum", "volatility", "derivatives_pressure"], model_id="pytest_model")
    scored = score_model(rows, model)

    assert model.model_id == "pytest_model"
    assert model.model_type == "weighted_score"
    assert set(model.features) == {"momentum", "volatility", "derivatives_pressure"}
    assert model.input_hash
    assert model.artifact_hash
    assert all("signal_score" in row and row["model_id"] == "pytest_model" for row in scored)


def test_equal_weight_score_model_uses_uniform_cpu_weights():
    rows = feature_rows()
    model = fit_weighted_score_model(
        rows,
        features=["momentum", "volatility", "derivatives_pressure"],
        model_id="equal_model",
        weight_mode="equal",
        model_type="walk_forward_equal_weight_score",
    )

    assert model.model_type == "walk_forward_equal_weight_score"
    assert model.metrics["weight_mode"] == "equal"
    assert model.weights == {"momentum": 1 / 3, "volatility": 1 / 3, "derivatives_pressure": 1 / 3}


def test_sign_weight_score_model_uses_correlation_sign_only():
    rows = feature_rows()
    model = fit_weighted_score_model(
        rows,
        features=["momentum", "derivatives_pressure"],
        model_id="sign_model",
        weight_mode="sign",
        model_type="walk_forward_sign_weight_score",
    )

    assert model.model_type == "walk_forward_sign_weight_score"
    assert model.metrics["weight_mode"] == "sign"
    assert set(model.weights) == {"momentum", "derivatives_pressure"}
    assert all(weight in {-1.0, -0.5, 0.0, 0.5, 1.0} for weight in model.weights.values())


def test_model_artifacts_are_persisted_with_signal_output(tmp_path: Path):
    rows = feature_rows()
    model = fit_weighted_score_model(rows, features=["momentum", "derivatives_pressure"], model_id="persisted_model")
    scored = score_model(rows, model)
    persisted = write_model_artifacts(tmp_path, model, scored)

    assert persisted.signal_output_path
    assert Path(persisted.signal_output_path).exists()
    assert (tmp_path / "persisted_model.model.json").exists()
    assert "artifact_hash" in (tmp_path / "persisted_model.model.json").read_text()


def test_model_artifact_hash_is_deterministic_for_same_inputs():
    rows = feature_rows()
    first = fit_weighted_score_model(rows, features=["momentum", "derivatives_pressure"], model_id="stable_model")
    second = fit_weighted_score_model(rows, features=["momentum", "derivatives_pressure"], model_id="stable_model")
    assert first.artifact_hash == second.artifact_hash


def test_walk_forward_model_scores_only_out_of_sample_windows():
    rows = feature_rows()
    model, scored = fit_walk_forward_weighted_score_model(
        rows,
        features=["momentum", "derivatives_pressure"],
        model_id="wf_model",
        train_periods=2,
        test_periods=1,
    )

    assert model.model_type == "walk_forward_weighted_score"
    assert model.metrics["walk_forward"] is True
    assert model.metrics["folds"]
    assert model.metrics["folds"][0]["n_train"] == 2
    assert scored
    assert all(row["model_id"] == "wf_model" for row in scored)
    assert all(row["test_start"] > row["train_end"] for row in scored)


def test_walk_forward_equal_model_family_preserves_oos_contract():
    rows = feature_rows()
    model, scored = fit_walk_forward_weighted_score_model(
        rows,
        features=["momentum", "derivatives_pressure"],
        model_id="wf_equal",
        train_periods=2,
        test_periods=1,
        model_family="walk_forward_equal_weight_score",
    )

    assert model.model_type == "walk_forward_equal_weight_score"
    assert model.metrics["weight_mode"] == "equal"
    assert model.metrics["folds"][0]["weights"] == {"momentum": 0.5, "derivatives_pressure": 0.5}
    assert scored
    assert all(row["test_start"] > row["train_end"] for row in scored)


def test_walk_forward_random_forest_scores_oos_and_records_importance():
    rows = feature_rows()
    model, scored = fit_walk_forward_random_forest_model(
        rows,
        features=["momentum", "derivatives_pressure"],
        model_id="wf_rf",
        train_periods=2,
        test_periods=1,
        n_estimators=5,
        max_depth=2,
        min_samples_leaf=1,
        random_state=7,
    )

    assert model.model_type == "walk_forward_random_forest"
    assert model.metrics["estimator"] == "sklearn.ensemble.RandomForestRegressor"
    assert model.metrics["n_estimators"] == 5
    assert model.metrics["folds"][0]["feature_importances"]
    assert set(model.weights) == {"momentum", "derivatives_pressure"}
    assert scored
    assert all(row["model_id"] == "wf_rf" for row in scored)
    assert all(row["test_start"] > row["train_end"] for row in scored)
