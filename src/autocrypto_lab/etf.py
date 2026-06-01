"""Source-backed U.S. spot BTC ETF event registry."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Source:
    title: str
    url: str
    note: str


@dataclass(frozen=True)
class EventWindow:
    name: str
    anchor_date: date
    start: date
    end: date
    sources: tuple[Source, ...]
    interpretation: str


def window(name: str, anchor: date, days_before: int, days_after: int, sources: tuple[Source, ...], interpretation: str) -> EventWindow:
    return EventWindow(
        name=name,
        anchor_date=anchor,
        start=anchor - timedelta(days=days_before),
        end=anchor + timedelta(days=days_after),
        sources=sources,
        interpretation=interpretation,
    )


SEC_APPROVAL = Source(
    title="SEC statement on spot bitcoin exchange-traded products",
    url="https://www.sec.gov/newsroom/speeches-statements/gensler-statement-spot-bitcoin-011023",
    note="SEC statement dated Jan. 10, 2024 says the Commission approved listing and trading of spot bitcoin ETP shares.",
)
NASDAQ_IBIT_DEBUT = Source(
    title="Nasdaq: BlackRock's IBIT debuts on Nasdaq",
    url="https://www.nasdaq.com/press-release/blackrocks-ibit-debuts-on-nasdaq-2024-01-11",
    note="Nasdaq press release dated Jan. 11, 2024 anchors first trading/debut for IBIT.",
)
CBOE_ARKB_LISTING = Source(
    title="Cboe ARKB new listing details",
    url="https://www.cboe.com/us/equities/notices/new_listings/details/?etf=true&firm_name=ARK+21+Shares&first_trade_dt=2024-01-11&ipo=true&symbols=ARKB",
    note="Cboe listing notice records first trade date Jan. 11, 2024 for ARKB.",
)


def default_etf_windows() -> tuple[EventWindow, ...]:
    approval = date(2024, 1, 10)
    trading = date(2024, 1, 11)
    return (
        window("approval_7d", approval, 7, 7, (SEC_APPROVAL,), "short event window around SEC approval"),
        window("first_trading_14d", trading, 14, 14, (NASDAQ_IBIT_DEBUT, CBOE_ARKB_LISTING), "initial ETF trading window"),
        window("initial_flow_stabilization_60d", trading, 0, 60, (SEC_APPROVAL, NASDAQ_IBIT_DEBUT), "early post-launch stabilization window"),
    )


def source_urls() -> set[str]:
    return {source.url for event in default_etf_windows() for source in event.sources}
