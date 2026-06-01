from datetime import datetime, timezone
from pathlib import Path

from autocrypto_lab.factors import build_public_futures_feature_table
from autocrypto_lab.models import fit_weighted_score_model, score_model, write_model_artifacts


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


def test_model_artifacts_are_persisted_with_signal_output(tmp_path: Path):
    rows = feature_rows()
    model = fit_weighted_score_model(rows, features=["momentum", "derivatives_pressure"], model_id="persisted_model")
    scored = score_model(rows, model)
    persisted = write_model_artifacts(tmp_path, model, scored)

    assert persisted.signal_output_path
    assert Path(persisted.signal_output_path).exists()
    assert (tmp_path / "persisted_model.model.json").exists()
    assert "artifact_hash" in (tmp_path / "persisted_model.model.json").read_text()
