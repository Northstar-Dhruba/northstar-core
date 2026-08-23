"""Reference contract test suite for the Quote market observation.

This suite defines the Northstar Reference Market Observation contract for
Quote.
"""

import pytest

from northstar_core.domain.exchange import Exchange
from northstar_core.domain.instrument import Instrument
from northstar_core.domain.listing import Listing
from northstar_core.domain.value_objects import ListingStatus, Tradability
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import (
    Currency,
    ExchangeCode,
    PointInTime,
    Price,
    Symbol,
)
from northstar_core.market_data import InvalidQuoteError, Quote
from northstar_core.market_data.value_objects import QuotedMarketState


def _build_listing() -> Listing:
    instrument = Instrument(Symbol("AAPL"), "Apple Inc.", "Equity")
    exchange = Exchange(ExchangeCode("NASDAQ"), "NASDAQ")
    return Listing(
        instrument,
        exchange,
        Currency("USD"),
        ListingStatus("Active"),
        Tradability("Permitted"),
    )


def _build_point_in_time() -> PointInTime:
    return PointInTime("2026-08-17T09:30:00Z")


def _build_quoted_market_state() -> QuotedMarketState:
    return QuotedMarketState((Price("100", Currency("USD")),))


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_quote_from_listing_point_in_time_and_quoted_market_state():
    listing = _build_listing()
    point_in_time = _build_point_in_time()
    quoted_market_state = _build_quoted_market_state()

    quote = Quote(listing, point_in_time, quoted_market_state)

    assert quote.listing is listing
    assert quote.point_in_time == point_in_time
    assert quote.quoted_market_state == quoted_market_state


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none_listing():
    with pytest.raises(InvalidQuoteError, match="listing cannot be None"):
        Quote(None, _build_point_in_time(), _build_quoted_market_state())


def test_rejects_none_point_in_time():
    with pytest.raises(InvalidQuoteError, match="point-in-time context cannot be None"):
        Quote(_build_listing(), None, _build_quoted_market_state())


def test_rejects_none_quoted_market_state():
    with pytest.raises(InvalidQuoteError, match="quoted market state cannot be None"):
        Quote(_build_listing(), _build_point_in_time(), None)


def test_rejects_invalid_listing_type():
    with pytest.raises(InvalidQuoteError, match="listing must be a Listing"):
        Quote("listing", _build_point_in_time(), _build_quoted_market_state())


def test_rejects_invalid_point_in_time_type():
    with pytest.raises(InvalidQuoteError, match="point-in-time context must be a PointInTime"):
        Quote(_build_listing(), "2026-08-17T09:30:00Z", _build_quoted_market_state())


def test_rejects_invalid_quoted_market_state_type():
    with pytest.raises(InvalidQuoteError, match="quoted market state must be a QuotedMarketState"):
        Quote(_build_listing(), _build_point_in_time(), "100 USD")


def test_invalid_quote_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        Quote(None, _build_point_in_time(), _build_quoted_market_state())


def test_invalid_quote_error_is_a_value_error():
    with pytest.raises(ValueError):
        Quote(None, _build_point_in_time(), _build_quoted_market_state())


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def test_quote_composes_listing_point_in_time_and_quoted_market_state():
    listing = _build_listing()
    point_in_time = _build_point_in_time()
    quoted_market_state = _build_quoted_market_state()

    quote = Quote(listing, point_in_time, quoted_market_state)

    assert isinstance(quote.listing, Listing)
    assert isinstance(quote.point_in_time, PointInTime)
    assert isinstance(quote.quoted_market_state, QuotedMarketState)


def test_quote_does_not_directly_own_instrument_exchange_or_workflow_objects():
    quote = Quote(_build_listing(), _build_point_in_time(), _build_quoted_market_state())

    assert not hasattr(quote, "instrument")
    assert not hasattr(quote, "exchange")
    assert not hasattr(quote, "listing_status")
    assert not hasattr(quote, "tradability")
    assert not hasattr(quote, "price")
    assert not hasattr(quote, "money")
    assert not hasattr(quote, "orders")
    assert not hasattr(quote, "trades")
    assert not hasattr(quote, "positions")
    assert not hasattr(quote, "portfolio")


def test_quoted_market_state_remains_owner_of_quote_specific_business_meaning():
    quote = Quote(_build_listing(), _build_point_in_time(), _build_quoted_market_state())

    assert hasattr(quote.quoted_market_state, "quotation_values")


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_quotes_compare_equal_when_composed_values_are_equal():
    listing = _build_listing()
    quoted_market_state = _build_quoted_market_state()

    left = Quote(listing, PointInTime("2026-08-17T09:30:00Z"), quoted_market_state)
    right = Quote(listing, PointInTime("2026-08-17T14:30:00+05:00"), quoted_market_state)

    assert left == right


def test_different_observation_meaning_does_not_compare_equal():
    listing = _build_listing()
    point_in_time = _build_point_in_time()

    left = Quote(listing, point_in_time, QuotedMarketState((Price("100", Currency("USD")),)))
    right = Quote(listing, point_in_time, QuotedMarketState((Price("101", Currency("USD")),)))

    assert left != right


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_quotes_have_equal_hashes():
    listing = _build_listing()
    quoted_market_state = _build_quoted_market_state()

    left = Quote(listing, PointInTime("2026-08-17T09:30:00Z"), quoted_market_state)
    right = Quote(listing, PointInTime("2026-08-17T14:30:00+05:00"), quoted_market_state)

    assert hash(left) == hash(right)


def test_quote_is_usable_as_dictionary_key():
    listing = _build_listing()
    key = Quote(listing, PointInTime("2026-08-17T09:30:00Z"), _build_quoted_market_state())
    index = {key: "observation"}

    probe = Quote(
        listing,
        PointInTime("2026-08-17T14:30:00+05:00"),
        _build_quoted_market_state(),
    )

    assert index[probe] == "observation"


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_concise_deterministic_business_representation():
    quote = Quote(_build_listing(), _build_point_in_time(), _build_quoted_market_state())

    assert str(quote) == "AAPL@NASDAQ 2026-08-17T09:30:00Z 100 USD"


def test_repr_contains_quote_and_composed_components():
    quote = Quote(_build_listing(), _build_point_in_time(), _build_quoted_market_state())
    representation = repr(quote)

    assert "Quote(" in representation
    assert "Listing(" in representation
    assert "PointInTime(" in representation
    assert "QuotedMarketState(" in representation


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_quote_is_immutable():
    quote = Quote(_build_listing(), _build_point_in_time(), _build_quoted_market_state())

    with pytest.raises(AttributeError):
        quote.point_in_time = PointInTime("2026-08-17T09:30:01Z")


def test_quote_does_not_support_ordering():
    left = Quote(
        _build_listing(), PointInTime("2026-08-17T09:30:00Z"), _build_quoted_market_state()
    )
    right = Quote(
        _build_listing(),
        PointInTime("2026-08-17T09:30:01Z"),
        _build_quoted_market_state(),
    )

    with pytest.raises(TypeError):
        _ = left < right


def test_aggregate_ownership_is_preserved():
    listing = _build_listing()
    point_in_time = _build_point_in_time()
    quoted_market_state = _build_quoted_market_state()

    quote = Quote(listing, point_in_time, quoted_market_state)

    assert quote.listing is listing
    assert quote.point_in_time is point_in_time
    assert quote.quoted_market_state is quoted_market_state


def test_composed_objects_remain_unchanged_by_quote_construction():
    listing = _build_listing()
    point_in_time = _build_point_in_time()
    quoted_market_state = _build_quoted_market_state()

    listing_repr_before = repr(listing)
    point_in_time_value_before = point_in_time.value
    quoted_market_state_repr_before = repr(quoted_market_state)

    _ = Quote(listing, point_in_time, quoted_market_state)

    assert repr(listing) == listing_repr_before
    assert point_in_time.value == point_in_time_value_before
    assert repr(quoted_market_state) == quoted_market_state_repr_before
