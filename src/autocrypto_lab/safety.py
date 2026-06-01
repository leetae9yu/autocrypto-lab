"""Safety boundaries: no execution, and public-only mode for research backtests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

FORBIDDEN_ORDER_TERMS = (
    "create_order",
    "cancel_order",
    "place_order",
    "market_order",
    "limit_order",
    "change_position",
)

FORBIDDEN_PRIVATE_TERMS = (
    "api_key",
    "api_secret",
    "secret_key",
    "signature",
    "signed",
    "auth",
    "private",
    "account",
    "listen_key",
)

FORBIDDEN_ROUTE_FRAGMENTS = (
    "/order",
    "/batchOrders",
    "/allOpenOrders",
    "/position",
    "/leverage",
    "/marginType",
    "/income",
    "/balance",
    "/account",
    "/listenKey",
)

FORBIDDEN_HTTP_METHODS = ("POST", "DELETE")


class SafetyViolation(ValueError):
    """Raised when config or adapter behavior crosses v1 safety boundaries."""


@dataclass(frozen=True)
class ReadOnlyExchangePolicy:
    allow_private_read: bool = True
    allow_trading: bool = False
    minimum_cadence_minutes: int = 60
    public_only: bool = False

    def validate(self) -> None:
        if self.allow_trading:
            raise SafetyViolation("v1 forbids trading-permission API usage and order endpoints")
        if self.public_only and self.allow_private_read:
            raise SafetyViolation("public-only phase forbids private/account reads and API-key usage")
        if self.minimum_cadence_minutes < 60:
            raise SafetyViolation("v1 forbids sub-hour scalping; cadence must be >= 60 minutes")


class ReadOnlyAccountAdapter:
    """Restricted account adapter shape for balance/position reads only."""

    capability = "read_only"

    def balances(self) -> dict[str, float]:
        return {}

    def positions(self) -> dict[str, float]:
        return {}


def assert_no_forbidden_adapter_methods(adapter: object) -> None:
    names = set(dir(adapter))
    unsafe = sorted(term for term in FORBIDDEN_ORDER_TERMS if term in names)
    if unsafe:
        raise SafetyViolation(f"unsafe order-like methods exposed: {unsafe}")


def assert_no_forbidden_config_keys(keys: Iterable[str]) -> None:
    lowered = {key.lower() for key in keys}
    unsafe = sorted(term for term in (*FORBIDDEN_ORDER_TERMS, *FORBIDDEN_PRIVATE_TERMS) if term in lowered)
    if unsafe:
        raise SafetyViolation(f"unsafe trading/private config keys are forbidden in this phase: {unsafe}")


def assert_public_route(method: str, path: str, headers: dict[str, str] | None = None) -> None:
    normalized_method = method.upper()
    if normalized_method in FORBIDDEN_HTTP_METHODS:
        raise SafetyViolation(f"public-only phase forbids exchange HTTP {normalized_method} actions")
    lower_path = path.lower()
    unsafe_routes = [fragment for fragment in FORBIDDEN_ROUTE_FRAGMENTS if fragment.lower() in lower_path]
    if unsafe_routes:
        raise SafetyViolation(f"public-only phase forbids private/signed route fragments: {unsafe_routes}")
    header_names = {name.lower() for name in (headers or {})}
    unsafe_headers = sorted(name for name in header_names if name in {"x-mbx-apikey", "authorization"})
    if unsafe_headers:
        raise SafetyViolation(f"public-only phase forbids auth headers: {unsafe_headers}")
