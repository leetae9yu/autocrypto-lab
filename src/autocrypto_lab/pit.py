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
