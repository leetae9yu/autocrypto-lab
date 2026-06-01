"""Public/free market-data adapter contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol
from urllib.parse import urlencode
import json
import urllib.request

from autocrypto_lab.config import CANONICAL_SYMBOLS, ConfigError, ExperimentConfig
from autocrypto_lab.safety import assert_public_route

BINANCE_USDM_BASE_URL = "https://fapi.binance.com"
BINANCE_PUBLIC_ARCHIVE_BASE_URL = "https://data.binance.vision/data/futures/um"
FUTURES_SYMBOLS = {asset: f"{asset}USDT" for asset in CANONICAL_SYMBOLS}
KLINE_LIMIT = 1500
FUNDING_LIMIT = 1000
PUBLIC_DATA_LIMIT = 500


def futures_symbol(asset: str) -> str:
    symbol = asset.upper()
    if symbol in FUTURES_SYMBOLS:
        return FUTURES_SYMBOLS[symbol]
    if symbol.endswith("USDT") and symbol[:-4] in FUTURES_SYMBOLS:
        return symbol
    raise ConfigError(f"unsupported public futures symbol: {asset}")


def epoch_ms(value: datetime) -> int:
    return int(value.astimezone(timezone.utc).timestamp() * 1000)


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


@dataclass(frozen=True)
class PublicFuturesRequest:
    endpoint: str
    params: dict[str, str | int]
    limit: int
    retention_note: str = ""

    @property
    def url(self) -> str:
        query = urlencode(self.params)
        assert_public_route("GET", f"{self.endpoint}?{query}")
        return f"{BINANCE_USDM_BASE_URL}{self.endpoint}?{query}"


class HTTPClient(Protocol):
    def get_json(self, url: str, headers: dict[str, str] | None = None) -> object:
        """Return JSON from a public GET URL."""


class UrllibHTTPClient:
    def get_json(self, url: str, headers: dict[str, str] | None = None) -> object:
        request = urllib.request.Request(url, headers=headers or {}, method="GET")
        with urllib.request.urlopen(request, timeout=20) as response:  # nosec: public market-data URL only
            return json.loads(response.read().decode("utf-8"))


def _chunk_windows(start: datetime, end: datetime, *, interval: str, limit: int) -> list[tuple[datetime, datetime]]:
    if interval.endswith("h"):
        step = timedelta(hours=int(interval[:-1]) * limit)
    elif interval.endswith("d"):
        step = timedelta(days=int(interval[:-1]) * limit)
    else:
        raise ConfigError("public futures chunking requires >=1h interval")
    windows = []
    cursor = start
    while cursor < end:
        nxt = min(end, cursor + step)
        windows.append((cursor, nxt))
        cursor = nxt
    return windows


class BinancePublicFuturesAdapter:
    """API-key-free Binance USDⓈ-M public futures market-data adapter."""

    name = "binance_usdm_public"

    def __init__(self, http: HTTPClient | None = None):
        self.http = http or UrllibHTTPClient()

    def plan_kline_requests(self, asset: str, interval: str, start: datetime, end: datetime) -> list[PublicFuturesRequest]:
        ExperimentConfig(run_id="binance_kline_plan", symbols=(asset.upper().removesuffix("USDT"),), interval=interval, public_only=True, allow_private_read=False).validate()
        symbol = futures_symbol(asset)
        return [
            PublicFuturesRequest(
                endpoint="/fapi/v1/klines",
                params={"symbol": symbol, "interval": interval, "startTime": epoch_ms(a), "endTime": epoch_ms(b), "limit": KLINE_LIMIT},
                limit=KLINE_LIMIT,
            )
            for a, b in _chunk_windows(start, end, interval=interval, limit=KLINE_LIMIT)
        ]

    def plan_funding_requests(self, asset: str, start: datetime, end: datetime) -> list[PublicFuturesRequest]:
        symbol = futures_symbol(asset)
        eight_hours = "8h"
        return [
            PublicFuturesRequest(
                endpoint="/fapi/v1/fundingRate",
                params={"symbol": symbol, "startTime": epoch_ms(a), "endTime": epoch_ms(b), "limit": FUNDING_LIMIT},
                limit=FUNDING_LIMIT,
            )
            for a, b in _chunk_windows(start, end, interval=eight_hours, limit=FUNDING_LIMIT)
        ]

    def open_interest_request(self, asset: str, period: str = "1h", start: datetime | None = None, end: datetime | None = None) -> PublicFuturesRequest:
        symbol = futures_symbol(asset)
        params: dict[str, str | int] = {"symbol": symbol, "period": period, "limit": PUBLIC_DATA_LIMIT}
        if start is not None:
            params["startTime"] = epoch_ms(start)
        if end is not None:
            params["endTime"] = epoch_ms(end)
        return PublicFuturesRequest(
            endpoint="/futures/data/openInterestHist",
            params=params,
            limit=PUBLIC_DATA_LIMIT,
            retention_note="Binance public open interest statistics endpoint documents latest 1 month availability.",
        )

    def basis_request(self, asset: str, period: str = "1h", start: datetime | None = None, end: datetime | None = None) -> PublicFuturesRequest:
        symbol = futures_symbol(asset)
        params: dict[str, str | int] = {"pair": symbol, "contractType": "PERPETUAL", "period": period, "limit": PUBLIC_DATA_LIMIT}
        if start is not None:
            params["startTime"] = epoch_ms(start)
        if end is not None:
            params["endTime"] = epoch_ms(end)
        return PublicFuturesRequest(
            endpoint="/futures/data/basis",
            params=params,
            limit=PUBLIC_DATA_LIMIT,
            retention_note="Binance public basis endpoint documents latest 30 days availability.",
        )

    def public_archive_kline_metadata(self, asset: str, interval: str, yyyy_mm: str) -> dict[str, str]:
        symbol = futures_symbol(asset)
        filename = f"{symbol}-{interval}-{yyyy_mm}.zip"
        base = f"{BINANCE_PUBLIC_ARCHIVE_BASE_URL}/monthly/klines/{symbol}/{interval}/{filename}"
        return {"url": base, "checksum_url": f"{base}.CHECKSUM", "symbol": symbol, "interval": interval, "month": yyyy_mm}

    def fetch(self, request: PublicFuturesRequest) -> object:
        assert_public_route("GET", request.endpoint)
        return self.http.get_json(request.url, headers={})
