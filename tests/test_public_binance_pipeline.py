from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from autocrypto_lab.adapters import PublicFuturesRequest, epoch_ms, futures_symbol
from autocrypto_lab.pipeline import run_public_binance_pipeline


def ts(hour: int) -> datetime:
    return datetime(2026, 5, 31, hour, tzinfo=timezone.utc)


class FakeBinanceAdapter:
    def plan_kline_requests(self, asset: str, interval: str, start: datetime, end: datetime):
        return [PublicFuturesRequest("/fapi/v1/klines", {"symbol": futures_symbol(asset), "interval": interval, "startTime": epoch_ms(start), "endTime": epoch_ms(end), "limit": 1500}, 1500)]

    def plan_funding_requests(self, asset: str, start: datetime, end: datetime):
        return [PublicFuturesRequest("/fapi/v1/fundingRate", {"symbol": futures_symbol(asset), "startTime": epoch_ms(start), "endTime": epoch_ms(end), "limit": 1000}, 1000)]

    def open_interest_request(self, asset: str, period: str = "1h", start: datetime | None = None, end: datetime | None = None):
        return PublicFuturesRequest("/futures/data/openInterestHist", {"symbol": futures_symbol(asset), "period": period, "startTime": epoch_ms(start), "endTime": epoch_ms(end), "limit": 500}, 500)

    def basis_request(self, asset: str, period: str = "1h", start: datetime | None = None, end: datetime | None = None):
        return PublicFuturesRequest("/futures/data/basis", {"pair": futures_symbol(asset), "contractType": "PERPETUAL", "period": period, "startTime": epoch_ms(start), "endTime": epoch_ms(end), "limit": 500}, 500)

    def fetch(self, request: PublicFuturesRequest):
        symbol = str(request.params.get("symbol") or request.params.get("pair"))
        base = 100.0 if symbol.startswith("BTC") else 20.0
        if request.endpoint == "/fapi/v1/klines":
            return [
                [epoch_ms(ts(0)), str(base), str(base + 1), str(base - 1), str(base), "10", epoch_ms(ts(1)) - 1, "0", 1, "0", "0", "0"],
                [epoch_ms(ts(1)), str(base), str(base + 3), str(base), str(base + (3 if symbol.startswith("BTC") else -1)), "12", epoch_ms(ts(2)) - 1, "0", 1, "0", "0", "0"],
                [epoch_ms(ts(2)), str(base), str(base + 4), str(base), str(base + (4 if symbol.startswith("BTC") else 0)), "11", epoch_ms(ts(3)) - 1, "0", 1, "0", "0", "0"],
            ]
        if request.endpoint == "/fapi/v1/fundingRate":
            return [{"symbol": symbol, "fundingTime": epoch_ms(ts(0)), "fundingRate": "0.0001"}]
        if request.endpoint == "/futures/data/openInterestHist":
            return [{"symbol": symbol, "timestamp": epoch_ms(ts(0)), "sumOpenInterest": "1000"}]
        if request.endpoint == "/futures/data/basis":
            return [{"pair": symbol, "timestamp": epoch_ms(ts(0)), "basisRate": "0.0002"}]
        raise AssertionError(request.endpoint)


def test_public_binance_pipeline_downloads_normalizes_and_backtests(tmp_path: Path):
    outputs = run_public_binance_pipeline(
        tmp_path,
        {"run_id": "fake_live", "symbols": ["BTC", "ETH"], "interval": "1h", "factors": ["momentum", "volatility", "derivatives_pressure"]},
        start=ts(0),
        end=ts(3),
        adapter=FakeBinanceAdapter(),
        train_periods=2,
        test_periods=1,
    )

    assert outputs["report"].exists()
    assert outputs["model"].exists()
    assert outputs["signals"].exists()
    assert outputs["feature_table"].exists()
    assert outputs["metrics"].exists()
    manifest = json.loads(outputs["manifest"].read_text())
    assert manifest["source_metadata"]["source"] == "binance_usdm_public"
    assert manifest["source_metadata"]["walk_forward"] == {"train_periods": 2, "test_periods": 1, "step_periods": 1}
    lineage = manifest["source_metadata"]["artifact_lineage"]
    assert len(lineage["raw_data_snapshot_ids"]) == 8
    assert len(lineage["normalized_data_snapshot_ids"]) == 4
    assert lineage["feature_table_id"]
    assert lineage["model_artifact_id"]
    assert lineage["signal_artifact_id"]
    model = json.loads(outputs["model"].read_text())
    assert model["model_type"] == "walk_forward_weighted_score"
    assert model["metrics"]["walk_forward"] is True
    metrics = json.loads(outputs["metrics"].read_text())
    assert metrics["factor_model"] == model["model_id"]
    signals = json.loads(outputs["signals"].read_text())
    assert signals and all(row["test_start"] > row["train_end"] for row in signals)


def test_public_binance_pipeline_propagates_cpu_model_family(tmp_path: Path):
    outputs = run_public_binance_pipeline(
        tmp_path,
        {
            "run_id": "fake_live_equal",
            "symbols": ["BTC", "ETH"],
            "interval": "1h",
            "factors": ["momentum", "derivatives_pressure"],
            "model": "walk_forward_equal_weight_score",
        },
        start=ts(0),
        end=ts(3),
        adapter=FakeBinanceAdapter(),
        train_periods=2,
        test_periods=1,
    )

    manifest = json.loads(outputs["manifest"].read_text())
    model = json.loads(outputs["model"].read_text())
    assert manifest["source_metadata"]["model_family"] == "walk_forward_equal_weight_score"
    assert model["model_type"] == "walk_forward_equal_weight_score"
    assert model["metrics"]["weight_mode"] == "equal"
