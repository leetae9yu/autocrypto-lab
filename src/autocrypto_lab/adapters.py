"""Public/free market-data adapter contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from autocrypto_lab.config import CANONICAL_SYMBOLS, ConfigError, ExperimentConfig


@dataclass(frozen=True)
class MarketDataRequest:
    symbol: str
    interval: str
    source: str = "public"

    def validate(self) -> None:
        if self.symbol not in CANONICAL_SYMBOLS:
            raise ConfigError(f"unsupported v1 symbol: {self.symbol}")
        cfg = ExperimentConfig(run_id="adapter_validation", symbols=(self.symbol,), interval=self.interval)
        cfg.validate()
        if self.source != "public":
            raise ConfigError("v1 data adapters are public/free-data-first")


class PublicMarketDataAdapter(Protocol):
    name: str

    def fetch_ohlcv(self, request: MarketDataRequest) -> list[dict]:
        """Fetch public OHLCV rows for a request."""


class FixtureMarketDataAdapter:
    """Deterministic adapter for tests and CI smoke."""

    name = "fixture"

    def __init__(self, rows: list[dict]):
        self.rows = rows

    def fetch_ohlcv(self, request: MarketDataRequest) -> list[dict]:
        request.validate()
        return [row for row in self.rows if row.get("symbol") == request.symbol]
