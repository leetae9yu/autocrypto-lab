"""Typed experiment configuration for config-only research autonomy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from autocrypto_lab.safety import ReadOnlyExchangePolicy, assert_no_forbidden_config_keys

CANONICAL_SYMBOLS = ("BTC", "ETH", "SOL", "XRP")
ALLOWED_FACTORS = ("momentum", "reversal", "volatility", "flow", "derivatives_pressure")
ALLOWED_MODELS = ("baseline_mean",)
ALLOWED_CONFIG_KEYS = {
    "run_id",
    "symbols",
    "interval",
    "horizon_periods",
    "factors",
    "model",
    "fee_bps",
    "slippage_bps",
    "allow_private_read",
    "allow_trading",
    "public_only",
    "metadata",
}


class ConfigError(ValueError):
    """Raised when an experiment config violates v1 constraints."""


@dataclass(frozen=True)
class ExperimentConfig:
    run_id: str
    symbols: tuple[str, ...] = CANONICAL_SYMBOLS
    interval: str = "1h"
    horizon_periods: int = 1
    factors: tuple[Any, ...] = ("momentum",)
    model: str = "baseline_mean"
    fee_bps: float = 5.0
    slippage_bps: float = 2.0
    allow_private_read: bool = True
    allow_trading: bool = False
    public_only: bool = False
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
        if self.model not in ALLOWED_MODELS:
            raise ConfigError(f"unknown model for v1 registry: {self.model}")
        factor_names = [spec["name"] for spec in self.factor_specs()]
        unknown_factors = sorted(set(factor_names) - set(ALLOWED_FACTORS))
        if unknown_factors:
            raise ConfigError(f"unknown factors for v1 registry: {unknown_factors}")
        assert_no_forbidden_config_keys(self.metadata.keys())
        ReadOnlyExchangePolicy(
            allow_private_read=self.allow_private_read,
            allow_trading=self.allow_trading,
            minimum_cadence_minutes=self.cadence_minutes,
            public_only=self.public_only,
        ).validate()

    def factor_specs(self) -> list[dict[str, Any]]:
        """Normalize config factor declarations into safe declarative DSL specs."""
        specs: list[dict[str, Any]] = []
        for factor in self.factors:
            if isinstance(factor, str):
                specs.append({"name": factor})
                continue
            if isinstance(factor, Mapping):
                name = factor.get("name")
                if not isinstance(name, str) or not name:
                    raise ConfigError("factor mapping requires a non-empty name")
                params = factor.get("params", {})
                if not isinstance(params, Mapping):
                    raise ConfigError(f"factor {name} params must be a mapping")
                specs.append({"name": name, "params": dict(params)})
                continue
            raise ConfigError(f"unsupported factor declaration: {factor!r}")
        if not specs:
            raise ConfigError("at least one factor is required")
        return specs


def load_config(raw: Mapping[str, Any]) -> ExperimentConfig:
    assert_no_forbidden_config_keys(raw.keys())
    unknown = sorted(set(raw) - ALLOWED_CONFIG_KEYS)
    if unknown:
        raise ConfigError(f"unknown config keys: {unknown}")
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
        public_only=bool(raw.get("public_only", False)),
        metadata=dict(raw.get("metadata", {})),
    )
    cfg.validate()
    return cfg
