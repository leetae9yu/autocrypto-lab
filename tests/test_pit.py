from datetime import datetime, timezone

import pytest

from autocrypto_lab.pit import (
    PointInTimeError,
    validate_feature_label_order,
    validate_known_at,
    validate_no_post_event_pre_event_leak,
)


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
