"""Contract tests for MarketObservationContext."""

import pytest

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
from northstar_core.strategy import (
    InvalidMarketObservationContextError,
    MarketObservationContext,
)


def _build_context(listing: Listing | None = None) -> MarketObservationContext:
    currency = Currency("USD")
    listing = listing or Listing(
        Instrument(Symbol("AAPL"), "Apple Inc.", "Equity"),
        Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
        currency,
        ListingStatus("Active"),
        Tradability("Permitted"),
    )
    return MarketObservationContext(
        listing,
        PointInTime("2026-09-14T10:00:00Z"),
        Price("100", currency),
        Price("99", currency),
        Quantity("1000"),
        Price("101", currency),
        Price("98", currency),
        tuple(Price("100", currency) for _ in range(20)),
        tuple(Quantity("1000") for _ in range(20)),
    )


def test_context_validates_and_preserves_factual_observations() -> None:
    context = _build_context()

    assert context.latest_price.amount == 100
    assert context.previous_close.amount == 99
    assert len(context.recent_closes) == 20
    assert len(context.recent_volumes) == 20


def test_context_rejects_short_or_misaligned_history() -> None:
    context = _build_context()
    with pytest.raises(InvalidMarketObservationContextError):
        MarketObservationContext(
            context.listing,
            context.observed_at,
            context.latest_price,
            context.previous_close,
            context.latest_volume,
            context.daily_high,
            context.daily_low,
            context.recent_closes[:19],
            context.recent_volumes,
        )


def test_context_is_immutable_equal_and_hashable() -> None:
    left = _build_context()
    right = _build_context(left.listing)

    assert left == right
    assert hash(left) == hash(right)
    with pytest.raises(AttributeError):
        left.latest_price = right.previous_close
