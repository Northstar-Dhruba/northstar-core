"""Reference contract test suite for the OrderBook market observation.

This suite defines the Northstar Reference Market-Depth Observation contract
for OrderBook.
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
from northstar_core.market_data import InvalidOrderBookError, OrderBook
from northstar_core.market_data.value_objects import OrderBookState


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


def _build_order_book_state() -> OrderBookState:
    return OrderBookState((Price("100", Currency("USD")),))


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_order_book_from_listing_point_in_time_and_order_book_state():
    listing = _build_listing()
    point_in_time = _build_point_in_time()
    order_book_state = _build_order_book_state()

    order_book = OrderBook(listing, point_in_time, order_book_state)

    assert order_book.listing is listing
    assert order_book.point_in_time == point_in_time
    assert order_book.order_book_state == order_book_state


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none_listing():
    with pytest.raises(InvalidOrderBookError, match="listing cannot be None"):
        OrderBook(None, _build_point_in_time(), _build_order_book_state())


def test_rejects_none_point_in_time():
    with pytest.raises(InvalidOrderBookError, match="point-in-time context cannot be None"):
        OrderBook(_build_listing(), None, _build_order_book_state())


def test_rejects_none_order_book_state():
    with pytest.raises(InvalidOrderBookError, match="order book state cannot be None"):
        OrderBook(_build_listing(), _build_point_in_time(), None)


def test_rejects_invalid_listing_type():
    with pytest.raises(InvalidOrderBookError, match="listing must be a Listing"):
        OrderBook("listing", _build_point_in_time(), _build_order_book_state())


def test_rejects_invalid_point_in_time_type():
    with pytest.raises(InvalidOrderBookError, match="point-in-time context must be a PointInTime"):
        OrderBook(_build_listing(), "2026-08-17T09:30:00Z", _build_order_book_state())


def test_rejects_invalid_order_book_state_type():
    with pytest.raises(InvalidOrderBookError, match="order book state must be an OrderBookState"):
        OrderBook(_build_listing(), _build_point_in_time(), "100 USD")


def test_invalid_order_book_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        OrderBook(None, _build_point_in_time(), _build_order_book_state())


def test_invalid_order_book_error_is_a_value_error():
    with pytest.raises(ValueError):
        OrderBook(None, _build_point_in_time(), _build_order_book_state())


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def test_order_book_composes_listing_point_in_time_and_order_book_state():
    listing = _build_listing()
    point_in_time = _build_point_in_time()
    order_book_state = _build_order_book_state()

    order_book = OrderBook(listing, point_in_time, order_book_state)

    assert isinstance(order_book.listing, Listing)
    assert isinstance(order_book.point_in_time, PointInTime)
    assert isinstance(order_book.order_book_state, OrderBookState)


def test_order_book_does_not_directly_own_instrument_exchange_or_workflow_objects():
    order_book = OrderBook(_build_listing(), _build_point_in_time(), _build_order_book_state())

    assert not hasattr(order_book, "instrument")
    assert not hasattr(order_book, "exchange")
    assert not hasattr(order_book, "listing_status")
    assert not hasattr(order_book, "tradability")
    assert not hasattr(order_book, "price")
    assert not hasattr(order_book, "money")
    assert not hasattr(order_book, "orders")
    assert not hasattr(order_book, "trades")
    assert not hasattr(order_book, "positions")
    assert not hasattr(order_book, "portfolio")


def test_order_book_state_remains_owner_of_market_depth_observation_meaning():
    order_book = OrderBook(_build_listing(), _build_point_in_time(), _build_order_book_state())

    assert hasattr(order_book.order_book_state, "quotation_values")


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_order_books_compare_equal_when_composed_values_are_equal():
    listing = _build_listing()
    order_book_state = _build_order_book_state()

    left = OrderBook(listing, PointInTime("2026-08-17T09:30:00Z"), order_book_state)
    right = OrderBook(listing, PointInTime("2026-08-17T14:30:00+05:00"), order_book_state)

    assert left == right


def test_different_market_depth_observation_meaning_does_not_compare_equal():
    listing = _build_listing()
    point_in_time = _build_point_in_time()

    left = OrderBook(listing, point_in_time, OrderBookState((Price("100", Currency("USD")),)))
    right = OrderBook(listing, point_in_time, OrderBookState((Price("101", Currency("USD")),)))

    assert left != right


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_order_books_have_equal_hashes():
    listing = _build_listing()
    order_book_state = _build_order_book_state()

    left = OrderBook(listing, PointInTime("2026-08-17T09:30:00Z"), order_book_state)
    right = OrderBook(listing, PointInTime("2026-08-17T14:30:00+05:00"), order_book_state)

    assert hash(left) == hash(right)


def test_order_book_is_usable_as_dictionary_key():
    listing = _build_listing()
    key = OrderBook(listing, PointInTime("2026-08-17T09:30:00Z"), _build_order_book_state())
    index = {key: "market-depth-observation"}

    probe = OrderBook(
        listing,
        PointInTime("2026-08-17T14:30:00+05:00"),
        _build_order_book_state(),
    )

    assert index[probe] == "market-depth-observation"


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_concise_deterministic_business_representation():
    order_book = OrderBook(_build_listing(), _build_point_in_time(), _build_order_book_state())

    assert str(order_book) == "AAPL@NASDAQ 2026-08-17T09:30:00Z 100 USD"


def test_repr_contains_order_book_and_composed_components():
    order_book = OrderBook(_build_listing(), _build_point_in_time(), _build_order_book_state())
    representation = repr(order_book)

    assert "OrderBook(" in representation
    assert "Listing(" in representation
    assert "PointInTime(" in representation
    assert "OrderBookState(" in representation


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_order_book_is_immutable():
    order_book = OrderBook(_build_listing(), _build_point_in_time(), _build_order_book_state())

    with pytest.raises(AttributeError):
        order_book.point_in_time = PointInTime("2026-08-17T09:30:01Z")


def test_order_book_does_not_support_ordering():
    left = OrderBook(
        _build_listing(),
        PointInTime("2026-08-17T09:30:00Z"),
        _build_order_book_state(),
    )
    right = OrderBook(
        _build_listing(),
        PointInTime("2026-08-17T09:30:01Z"),
        _build_order_book_state(),
    )

    with pytest.raises(TypeError):
        _ = left < right


def test_aggregate_ownership_is_preserved():
    listing = _build_listing()
    point_in_time = _build_point_in_time()
    order_book_state = _build_order_book_state()

    order_book = OrderBook(listing, point_in_time, order_book_state)

    assert order_book.listing is listing
    assert order_book.point_in_time is point_in_time
    assert order_book.order_book_state is order_book_state


def test_composed_objects_remain_unchanged_by_order_book_construction():
    listing = _build_listing()
    point_in_time = _build_point_in_time()
    order_book_state = _build_order_book_state()

    listing_repr_before = repr(listing)
    point_in_time_value_before = point_in_time.value
    order_book_state_repr_before = repr(order_book_state)

    _ = OrderBook(listing, point_in_time, order_book_state)

    assert repr(listing) == listing_repr_before
    assert point_in_time.value == point_in_time_value_before
    assert repr(order_book_state) == order_book_state_repr_before
