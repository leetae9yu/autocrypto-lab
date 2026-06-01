"""Point-in-time validation helpers."""

from __future__ import annotations

from typing import Any


class PointInTimeError(AssertionError):
    pass


def validate_feature_label_order(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        label_ts = row.get("label_timestamp", row["timestamp"])
        if row["timestamp"] > label_ts:
            raise PointInTimeError("feature timestamp occurs after label timestamp")


def validate_known_at(rows: list[dict[str, Any]], known_at_field: str = "known_at") -> None:
    for row in rows:
        known_at = row.get(known_at_field, row["timestamp"])
        if known_at > row["timestamp"]:
            raise PointInTimeError("feature is not known at formation timestamp")


def validate_no_post_event_pre_event_leak(rows: list[dict[str, Any]], event_timestamp: Any, regime_field: str = "regime") -> None:
    for row in rows:
        if row.get(regime_field) == "pre" and row["timestamp"] >= event_timestamp:
            raise PointInTimeError("pre-event regime contains post-event timestamp")
