"""Typed experiment configuration for config-only research autonomy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from autocrypto_lab.safety import ReadOnlyExchangePolicy, assert_no_forbidden_config_keys

CANONICAL_SYMBOLS = ("BTC", "ETH", "SOL", "XRP")


class ConfigError(ValueError):
    """Raised when an experiment config violates v1 constraints."""


@dataclass(frozen=True)
class ExperimentConfig:
    run_id: str
    symbols: tuple[str, ...] = CANONICAL_SYMBOLS
    interval: str = "1h"
    horizon_periods: int = 1
    factors: tuple[str, ...] = ("momentum",)
    model: str = "baseline_mean"
    fee_bps: float = 5.0
    slippage_bps: float = 2.0
    allow_private_read: bool = True
    allow_trading: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def cadence_minutes(self) -> int:
        if self.interval.endswith("h"):
            return int(self.interval[:-1]) * 60
        if self.interval.endswith("d"):
            return int(self.interval[:-1]) * 24 * 60
        if self.interval.endswith("m"):
            return int(self.interval[:-1])
        raise ConfigError(f"unsupported interval: {self.interval}")

    def validate(self) -> None:
        if not self.run_id:
            raise ConfigError("run_id is required")
        unknown = sorted(set(self.symbols) - set(CANONICAL_SYMBOLS))
        if unknown:
            raise ConfigError(f"unknown symbols for v1 universe: {unknown}")
        if self.cadence_minutes < 60:
            raise ConfigError("interval must be >= 1h")
        if self.horizon_periods < 1:
            raise ConfigError("horizon_periods must be positive")
        assert_no_forbidden_config_keys(self.metadata.keys())
        ReadOnlyExchangePolicy(
            allow_private_read=self.allow_private_read,
            allow_trading=self.allow_trading,
            minimum_cadence_minutes=self.cadence_minutes,
        ).validate()


def load_config(raw: Mapping[str, Any]) -> ExperimentConfig:
    cfg = ExperimentConfig(
        run_id=str(raw.get("run_id", "")),
        symbols=tuple(raw.get("symbols", CANONICAL_SYMBOLS)),
        interval=str(raw.get("interval", "1h")),
        horizon_periods=int(raw.get("horizon_periods", 1)),
        factors=tuple(raw.get("factors", ("momentum",))),
        model=str(raw.get("model", "baseline_mean")),
        fee_bps=float(raw.get("fee_bps", 5.0)),
        slippage_bps=float(raw.get("slippage_bps", 2.0)),
        allow_private_read=bool(raw.get("allow_private_read", True)),
        allow_trading=bool(raw.get("allow_trading", False)),
        metadata=dict(raw.get("metadata", {})),
    )
    cfg.validate()
    return cfg
