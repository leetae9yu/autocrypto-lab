from datetime import datetime, timezone

import pytest

from autocrypto_lab.pit import (
    PointInTimeError,
    validate_feature_label_order,
    validate_known_at,
    validate_no_post_event_pre_event_leak,
)
from autocrypto_lab.factors import build_public_futures_feature_table


def ts(hour: int):
    return datetime(2024, 1, 10, hour, tzinfo=timezone.utc)


def test_feature_after_label_fails():
    with pytest.raises(PointInTimeError, match="after label"):
        validate_feature_label_order([{"timestamp": ts(2), "label_timestamp": ts(1)}])


def test_future_known_at_fails():
    with pytest.raises(PointInTimeError, match="not known"):
        validate_known_at([{"timestamp": ts(1), "known_at": ts(2)}])


def test_valid_known_at_passes():
    validate_known_at([{"timestamp": ts(2), "known_at": ts(1)}])


def test_terminal_unavailable_label_can_be_marked_without_leakage():
    validate_feature_label_order([{"timestamp": ts(2), "label_timestamp": ts(2), "label_available": False}])


def test_pre_event_window_cannot_contain_post_event_timestamp():
    with pytest.raises(PointInTimeError, match="pre-event"):
        validate_no_post_event_pre_event_leak([{"timestamp": ts(2), "regime": "pre"}], event_timestamp=ts(1))


def test_public_futures_feature_table_uses_latest_known_sources_only():
    klines = [
        {"timestamp": ts(0), "symbol": "BTCUSDT", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 10.0},
        {"timestamp": ts(1), "symbol": "BTCUSDT", "open": 100.0, "high": 103.0, "low": 100.0, "close": 102.0, "volume": 12.0},
        {"timestamp": ts(2), "symbol": "BTCUSDT", "open": 102.0, "high": 104.0, "low": 101.0, "close": 103.0, "volume": 11.0},
    ]
    funding = [
        {"timestamp": ts(0), "symbol": "BTCUSDT", "funding_rate": 0.0001},
        {"timestamp": ts(2), "symbol": "BTCUSDT", "funding_rate": 0.9999},
    ]
    open_interest = [{"timestamp": ts(0), "symbol": "BTCUSDT", "open_interest": 1000.0}]
    basis = [{"timestamp": ts(0), "symbol": "BTCUSDT", "spot_future_basis": 12.0}]

    rows = build_public_futures_feature_table(klines, funding, open_interest, basis, horizon=1)
    formation_at_one = [row for row in rows if row["timestamp"] == ts(1)][0]
    assert formation_at_one["funding_rate"] == 0.0001
    assert formation_at_one["source_known_at"]["funding"] == ts(0)
    assert formation_at_one["label_timestamp"] == ts(2)
    validate_known_at(rows)
    validate_feature_label_order(rows)


def test_public_futures_feature_table_does_not_use_future_funding():
    klines = [
        {"timestamp": ts(0), "symbol": "ETHUSDT", "open": 10.0, "high": 11.0, "low": 9.0, "close": 10.0, "volume": 1.0},
        {"timestamp": ts(1), "symbol": "ETHUSDT", "open": 10.0, "high": 12.0, "low": 10.0, "close": 11.0, "volume": 1.0},
    ]
    rows = build_public_futures_feature_table(
        klines,
        funding=[{"timestamp": ts(1), "symbol": "ETHUSDT", "funding_rate": 0.123}],
        open_interest=[],
        basis=[],
    )
    assert rows[0]["funding_rate"] == 0.0
    assert rows[0]["source_known_at"]["funding"] is None


def test_public_futures_feature_table_respects_source_known_at():
    klines = [
        {"timestamp": ts(1), "symbol": "SOLUSDT", "open": 10.0, "high": 11.0, "low": 9.0, "close": 10.0, "volume": 1.0},
        {"timestamp": ts(2), "symbol": "SOLUSDT", "open": 10.0, "high": 12.0, "low": 10.0, "close": 11.0, "volume": 1.0},
    ]
    rows = build_public_futures_feature_table(
        klines,
        funding=[{"timestamp": ts(0), "known_at": ts(2), "symbol": "SOLUSDT", "funding_rate": 0.123}],
        open_interest=[],
        basis=[],
    )
    assert rows[0]["funding_rate"] == 0.0
    assert rows[1]["funding_rate"] == 0.123
    assert rows[1]["source_known_at"]["funding"] == ts(2)
