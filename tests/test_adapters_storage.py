from pathlib import Path

import pytest

from autocrypto_lab.adapters import FixtureMarketDataAdapter, MarketDataRequest
from autocrypto_lab.config import ConfigError
from autocrypto_lab.data import load_ohlcv_csv
from autocrypto_lab.storage import write_snapshot


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
