"""Contract tests for MarketObservationContext."""

import pytest

from northstar_core.domain.value_objects import ListingReference
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

_USD = Currency("USD")
_EUR = Currency("EUR")
_UNSET = object()


def _reference() -> ListingReference:
    return ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))


def _build_context(
    listing_reference: object = _UNSET,
    *,
    latest_price: object = _UNSET,
    previous_close: object = _UNSET,
    daily_high: object = _UNSET,
    daily_low: object = _UNSET,
    recent_closes: object = _UNSET,
    recent_volumes: object = _UNSET,
) -> MarketObservationContext:
    default_closes = tuple(Price("100", _USD) for _ in range(20))
    default_volumes = tuple(Quantity("1000") for _ in range(20))
    return MarketObservationContext(
        _reference() if listing_reference is _UNSET else listing_reference,
        PointInTime("2026-09-14T10:00:00Z"),
        Price("100", _USD) if latest_price is _UNSET else latest_price,
        Price("99", _USD) if previous_close is _UNSET else previous_close,
        Quantity("1000"),
        Price("101", _USD) if daily_high is _UNSET else daily_high,
        Price("98", _USD) if daily_low is _UNSET else daily_low,
        default_closes if recent_closes is _UNSET else recent_closes,
        default_volumes if recent_volumes is _UNSET else recent_volumes,
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_context_validates_and_preserves_factual_observations() -> None:
    context = _build_context()

    assert context.latest_price.amount == 100
    assert context.previous_close.amount == 99
    assert len(context.recent_closes) == 20
    assert len(context.recent_volumes) == 20


def test_context_accepts_valid_listing_reference() -> None:
    reference = _reference()
    context = _build_context(reference)

    assert context.listing_reference is reference
    assert context.listing_reference.symbol == Symbol("AAPL")
    assert context.listing_reference.exchange_code == ExchangeCode("NASDAQ")


def test_context_does_not_expose_a_listing_entity() -> None:
    context = _build_context()

    assert not hasattr(context, "listing")


# ---------------------------------------------------------------------------
# Listing reference validation
# ---------------------------------------------------------------------------


def test_context_rejects_none_listing_reference() -> None:
    with pytest.raises(InvalidMarketObservationContextError, match="cannot be None"):
        _build_context(None)


def test_context_rejects_wrong_listing_reference_type() -> None:
    with pytest.raises(InvalidMarketObservationContextError, match="must be a ListingReference"):
        _build_context("AAPL@NASDAQ")


def test_context_rejects_symbol_supplied_as_listing_reference() -> None:
    with pytest.raises(InvalidMarketObservationContextError, match="must be a ListingReference"):
        _build_context(Symbol("AAPL"))


# ---------------------------------------------------------------------------
# Currency invariant
# ---------------------------------------------------------------------------


def test_latest_price_establishes_the_market_observation_currency() -> None:
    context = _build_context(
        latest_price=Price("100", _EUR),
        previous_close=Price("99", _EUR),
        daily_high=Price("101", _EUR),
        daily_low=Price("98", _EUR),
        recent_closes=tuple(Price("100", _EUR) for _ in range(20)),
    )

    assert context.latest_price.currency == _EUR
    assert context.previous_close.currency == _EUR


def test_context_accepts_consistent_currency_across_every_price_fact() -> None:
    context = _build_context()

    currencies = {
        context.latest_price.currency,
        context.previous_close.currency,
        context.daily_high.currency,
        context.daily_low.currency,
        *(price.currency for price in context.recent_closes),
    }

    assert currencies == {_USD}


def test_context_rejects_previous_close_currency_mismatch() -> None:
    with pytest.raises(
        InvalidMarketObservationContextError,
        match="previous close currency must match the market observation currency",
    ):
        _build_context(previous_close=Price("99", _EUR))


def test_context_rejects_daily_high_currency_mismatch() -> None:
    with pytest.raises(
        InvalidMarketObservationContextError,
        match="daily high currency must match the market observation currency",
    ):
        _build_context(daily_high=Price("101", _EUR))


def test_context_rejects_daily_low_currency_mismatch() -> None:
    with pytest.raises(
        InvalidMarketObservationContextError,
        match="daily low currency must match the market observation currency",
    ):
        _build_context(daily_low=Price("98", _EUR))


def test_context_rejects_any_recent_close_currency_mismatch() -> None:
    mixed = tuple(Price("100", _USD) for _ in range(19)) + (Price("100", _EUR),)

    with pytest.raises(
        InvalidMarketObservationContextError,
        match="recent closes currency must match the market observation currency",
    ):
        _build_context(recent_closes=mixed)


def test_context_error_message_no_longer_references_a_listing_currency() -> None:
    with pytest.raises(InvalidMarketObservationContextError) as error:
        _build_context(previous_close=Price("99", _EUR))

    assert "listing currency" not in str(error.value)


def test_context_does_not_require_currency_on_quantity_values() -> None:
    context = _build_context()

    assert not hasattr(context.latest_volume, "currency")
    assert all(not hasattr(volume, "currency") for volume in context.recent_volumes)


def test_context_does_not_expose_a_standalone_currency_field() -> None:
    context = _build_context()

    assert not hasattr(context, "currency")


# ---------------------------------------------------------------------------
# Price and volume validation
# ---------------------------------------------------------------------------


def test_context_rejects_none_latest_price() -> None:
    with pytest.raises(InvalidMarketObservationContextError, match="latest price cannot be None"):
        _build_context(latest_price=None)


def test_context_rejects_wrong_latest_price_type() -> None:
    with pytest.raises(InvalidMarketObservationContextError, match="must be a Price value"):
        MarketObservationContext(
            _reference(),
            PointInTime("2026-09-14T10:00:00Z"),
            "100",
            Price("99", _USD),
            Quantity("1000"),
            Price("101", _USD),
            Price("98", _USD),
            tuple(Price("100", _USD) for _ in range(20)),
            tuple(Quantity("1000") for _ in range(20)),
        )


def test_context_rejects_wrong_volume_type() -> None:
    with pytest.raises(InvalidMarketObservationContextError, match="must be a Quantity value"):
        _build_context(recent_volumes=tuple(["1000"] * 20))


# ---------------------------------------------------------------------------
# Preserved structural invariants
# ---------------------------------------------------------------------------


def test_context_rejects_short_recent_closes_history() -> None:
    with pytest.raises(InvalidMarketObservationContextError, match="at least 20 observations"):
        _build_context(recent_closes=tuple(Price("100", _USD) for _ in range(19)))


def test_context_rejects_short_recent_volumes_history() -> None:
    with pytest.raises(InvalidMarketObservationContextError, match="at least 20 observations"):
        _build_context(recent_volumes=tuple(Quantity("1000") for _ in range(19)))


def test_context_rejects_misaligned_history_lengths() -> None:
    with pytest.raises(InvalidMarketObservationContextError, match="equal lengths"):
        _build_context(
            recent_closes=tuple(Price("100", _USD) for _ in range(21)),
            recent_volumes=tuple(Quantity("1000") for _ in range(20)),
        )


def test_context_rejects_daily_low_greater_than_daily_high() -> None:
    with pytest.raises(
        InvalidMarketObservationContextError, match="daily low cannot exceed daily high"
    ):
        _build_context(daily_high=Price("98", _USD), daily_low=Price("101", _USD))


def test_context_accepts_daily_low_equal_to_daily_high() -> None:
    context = _build_context(daily_high=Price("100", _USD), daily_low=Price("100", _USD))

    assert context.daily_low == context.daily_high


def test_context_rejects_non_tuple_recent_closes() -> None:
    with pytest.raises(InvalidMarketObservationContextError, match="must be a tuple"):
        _build_context(recent_closes=[Price("100", _USD) for _ in range(20)])


# ---------------------------------------------------------------------------
# Value semantics
# ---------------------------------------------------------------------------


def test_context_is_immutable_equal_and_hashable() -> None:
    left = _build_context()
    right = _build_context(left.listing_reference)

    assert left == right
    assert hash(left) == hash(right)
    with pytest.raises(AttributeError):
        left.latest_price = right.previous_close


def test_contexts_with_equivalent_listing_references_compare_equal() -> None:
    left = _build_context(ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ")))
    right = _build_context(ListingReference(Symbol(" aapl "), ExchangeCode(" nasdaq ")))

    assert left == right
    assert hash(left) == hash(right)


def test_contexts_with_different_listing_references_do_not_compare_equal() -> None:
    left = _build_context(ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ")))
    right = _build_context(ListingReference(Symbol("MSFT"), ExchangeCode("NASDAQ")))

    assert left != right
