"""Tests for deterministic AssetAnalysis generation from market observations."""

from northstar_core.domain.exchange import Exchange
from northstar_core.domain.instrument import Instrument
from northstar_core.domain.listing import Listing
from northstar_core.domain.value_objects import ListingStatus, Tradability
from northstar_core.foundation.value_objects import (
    Currency,
    ExchangeCode,
    PointInTime,
    Price,
    Quantity,
    Symbol,
)
from northstar_core.strategy import AssetAnalysisGenerator, MarketObservationContext


def _build_listing() -> Listing:
    return Listing(
        instrument=Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
        exchange=Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
        currency=Currency("USD"),
        listing_status=ListingStatus("Active"),
        tradability=Tradability("Permitted"),
    )


def _build_context(
    *,
    latest_price: str,
    previous_close: str,
    recent_closes: tuple[str, ...],
) -> MarketObservationContext:
    currency = Currency("USD")
    return MarketObservationContext(
        listing=_build_listing(),
        observed_at=PointInTime("2026-09-11T16:00:00Z"),
        latest_price=Price(latest_price, currency),
        previous_close=Price(previous_close, currency),
        latest_volume=Quantity("200"),
        daily_high=Price("200", currency),
        daily_low=Price("100", currency),
        recent_closes=tuple(Price(value, currency) for value in recent_closes),
        recent_volumes=tuple(Quantity("100") for _ in recent_closes),
    )


def test_generates_strong_bullish_signal_from_rising_price_trend_and_volume() -> None:
    context = _build_context(
        latest_price="130",
        previous_close="120",
        recent_closes=tuple(["100"] * 15 + ["130"] * 5),
    )

    analysis = AssetAnalysisGenerator().generate(context)

    assert analysis.summarized_signals == ("strong bullish",)


def test_generates_strong_bearish_signal_from_falling_price_trend_and_volume() -> None:
    context = _build_context(
        latest_price="100",
        previous_close="110",
        recent_closes=tuple(["130"] * 15 + ["100"] * 5),
    )

    analysis = AssetAnalysisGenerator().generate(context)

    assert analysis.summarized_signals == ("strong bearish",)


def test_generates_neutral_signal_when_observations_do_not_confirm_a_trend() -> None:
    context = _build_context(
        latest_price="110",
        previous_close="110",
        recent_closes=tuple(["110"] * 20),
    )

    analysis = AssetAnalysisGenerator().generate(context)

    assert analysis.summarized_signals == ("neutral trend",)
