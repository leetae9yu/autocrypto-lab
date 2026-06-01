from pathlib import Path
from datetime import datetime, timezone, timedelta

import pytest

from autocrypto_lab.adapters import BinancePublicFuturesAdapter, FixtureMarketDataAdapter, MarketDataRequest, futures_symbol
from autocrypto_lab.config import ConfigError
from autocrypto_lab.data import load_ohlcv_csv
from autocrypto_lab.storage import write_public_normalized_artifact, write_public_raw_artifact, write_snapshot


def test_public_request_validates_cadence_and_symbol():
    MarketDataRequest(symbol="BTC", interval="1h").validate()
    with pytest.raises(ConfigError):
        MarketDataRequest(symbol="DOGE", interval="1h").validate()
    with pytest.raises(ConfigError):
        MarketDataRequest(symbol="BTC", interval="5m").validate()


def test_fixture_adapter_filters_symbol():
    rows = load_ohlcv_csv(Path("tests/fixtures/ohlcv_1h.csv"))
    out = FixtureMarketDataAdapter(rows).fetch_ohlcv(MarketDataRequest(symbol="ETH", interval="1h"))
    assert out
    assert {row["symbol"] for row in out} == {"ETH"}


def test_snapshot_manifest_records_metadata(tmp_path: Path):
    rows = load_ohlcv_csv(Path("tests/fixtures/ohlcv_1h.csv"))[:2]
    manifest = write_snapshot(tmp_path, "fixture", "BTC", "1h", rows, {"kind": "smoke"})
    assert manifest.row_count == 2
    assert Path(manifest.path).exists()
    assert (tmp_path / "fixture_BTC_1h.manifest.json").exists()


def test_futures_symbol_mapping_is_explicit():
    assert futures_symbol("BTC") == "BTCUSDT"
    assert futures_symbol("ETH") == "ETHUSDT"
    assert futures_symbol("SOL") == "SOLUSDT"
    assert futures_symbol("XRP") == "XRPUSDT"
    with pytest.raises(ConfigError, match="unsupported"):
        futures_symbol("DOGE")


def test_binance_public_kline_requests_are_keyless_and_chunked():
    adapter = BinancePublicFuturesAdapter()
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(hours=1501)
    requests = adapter.plan_kline_requests("BTC", "1h", start, end)

    assert len(requests) == 2
    assert requests[0].endpoint == "/fapi/v1/klines"
    assert requests[0].limit == 1500
    assert requests[0].params["symbol"] == "BTCUSDT"
    assert "signature" not in requests[0].url.lower()
    assert "api" not in requests[0].params


def test_binance_public_funding_and_retention_requests():
    adapter = BinancePublicFuturesAdapter()
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(hours=8 * 1001)

    funding = adapter.plan_funding_requests("ETH", start, end)
    assert len(funding) == 2
    assert funding[0].endpoint == "/fapi/v1/fundingRate"
    assert funding[0].limit == 1000

    oi = adapter.open_interest_request("BTC")
    basis = adapter.basis_request("BTC")
    assert oi.limit == 500
    assert "1 month" in oi.retention_note
    assert basis.limit == 500
    assert basis.params["contractType"] == "PERPETUAL"
    assert "30 days" in basis.retention_note


def test_binance_public_fetch_uses_no_auth_headers():
    calls = []

    class FakeHTTP:
        def get_json(self, url, headers=None):
            calls.append((url, headers))
            return [{"ok": True}]

    adapter = BinancePublicFuturesAdapter(http=FakeHTTP())
    result = adapter.fetch(adapter.open_interest_request("BTC"))
    assert result == [{"ok": True}]
    assert calls[0][1] == {}


def test_public_archive_metadata_contains_checksum_url():
    metadata = BinancePublicFuturesAdapter().public_archive_kline_metadata("BTC", "1h", "2024-01")
    assert metadata["url"].endswith("BTCUSDT-1h-2024-01.zip")
    assert metadata["checksum_url"].endswith(".CHECKSUM")


def test_public_raw_artifact_records_endpoint_schema_and_retention(tmp_path: Path):
    manifest = write_public_raw_artifact(
        tmp_path,
        source="binance_usdm_public",
        endpoint="/futures/data/openInterestHist",
        symbol="BTCUSDT",
        interval_or_period="1h",
        request_window={"start": "2024-01-01T00:00:00Z", "end": "2024-01-01T01:00:00Z"},
        rows=[{"sumOpenInterest": "100", "timestamp": 1704067200000}],
        retention_note="latest 1 month",
        checksum_url="https://example.test/checksum",
    )

    assert manifest.layer == "raw"
    assert manifest.endpoint == "/futures/data/openInterestHist"
    assert manifest.row_count == 1
    assert manifest.retention_note == "latest 1 month"
    assert manifest.checksum_url.endswith("checksum")
    assert Path(manifest.path).exists()
    assert Path(manifest.path.replace(".json", ".manifest.json")).exists()


def test_public_normalized_artifact_links_raw_ids(tmp_path: Path):
    raw = write_public_raw_artifact(
        tmp_path,
        source="binance_usdm_public",
        endpoint="/fapi/v1/fundingRate",
        symbol="BTCUSDT",
        interval_or_period="8h",
        request_window={"start": 1, "end": 2},
        rows=[{"fundingTime": 1, "fundingRate": "0.0001"}],
    )
    normalized = write_public_normalized_artifact(
        tmp_path,
        source="binance_usdm_public",
        endpoint="/fapi/v1/fundingRate",
        symbol="BTCUSDT",
        interval_or_period="8h",
        rows=[{"timestamp": "2024-01-01T00:00:00Z", "symbol": "BTCUSDT", "funding_rate": 0.0001}],
        fieldnames=["timestamp", "symbol", "funding_rate"],
        raw_artifact_ids=[raw.artifact_id],
    )

    assert normalized.layer == "normalized"
    assert normalized.metadata["raw_artifact_ids"] == [raw.artifact_id]
    assert normalized.content_hash
    assert Path(normalized.path).read_text().splitlines()[0] == "timestamp,symbol,funding_rate"
