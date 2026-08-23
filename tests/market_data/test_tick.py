"""Reference contract test suite for the Tick market observation.

This suite defines the Northstar Reference High-Frequency Point Market
Observation contract for Tick.
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
from northstar_core.market_data import InvalidTickError, Tick
from northstar_core.market_data.value_objects import TickState


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


def _build_tick_state() -> TickState:
    return TickState((Price("100", Currency("USD")),))


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_tick_from_listing_point_in_time_and_tick_state():
    listing = _build_listing()
    point_in_time = _build_point_in_time()
    tick_state = _build_tick_state()

    tick = Tick(listing, point_in_time, tick_state)

    assert tick.listing is listing
    assert tick.point_in_time == point_in_time
    assert tick.tick_state == tick_state


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none_listing():
    with pytest.raises(InvalidTickError, match="listing cannot be None"):
        Tick(None, _build_point_in_time(), _build_tick_state())


def test_rejects_none_point_in_time():
    with pytest.raises(InvalidTickError, match="point-in-time context cannot be None"):
        Tick(_build_listing(), None, _build_tick_state())


def test_rejects_none_tick_state():
    with pytest.raises(InvalidTickError, match="state cannot be None"):
        Tick(_build_listing(), _build_point_in_time(), None)


def test_rejects_invalid_listing_type():
    with pytest.raises(InvalidTickError, match="listing must be a Listing"):
        Tick("listing", _build_point_in_time(), _build_tick_state())


def test_rejects_invalid_point_in_time_type():
    with pytest.raises(InvalidTickError, match="point-in-time context must be a PointInTime"):
        Tick(_build_listing(), "2026-08-17T09:30:00Z", _build_tick_state())


def test_rejects_invalid_tick_state_type():
    with pytest.raises(InvalidTickError, match="state must be a TickState"):
        Tick(_build_listing(), _build_point_in_time(), "100 USD")


def test_invalid_tick_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        Tick(None, _build_point_in_time(), _build_tick_state())


def test_invalid_tick_error_is_a_value_error():
    with pytest.raises(ValueError):
        Tick(None, _build_point_in_time(), _build_tick_state())


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def test_tick_composes_listing_point_in_time_and_tick_state():
    listing = _build_listing()
    point_in_time = _build_point_in_time()
    tick_state = _build_tick_state()

    tick = Tick(listing, point_in_time, tick_state)

    assert isinstance(tick.listing, Listing)
    assert isinstance(tick.point_in_time, PointInTime)
    assert isinstance(tick.tick_state, TickState)


def test_tick_does_not_directly_own_instrument_exchange_or_workflow_objects():
    tick = Tick(_build_listing(), _build_point_in_time(), _build_tick_state())

    assert not hasattr(tick, "instrument")
    assert not hasattr(tick, "exchange")
    assert not hasattr(tick, "listing_status")
    assert not hasattr(tick, "tradability")
    assert not hasattr(tick, "price")
    assert not hasattr(tick, "money")
    assert not hasattr(tick, "orders")
    assert not hasattr(tick, "trades")
    assert not hasattr(tick, "positions")
    assert not hasattr(tick, "portfolio")


def test_tick_state_remains_owner_of_high_frequency_point_observation_meaning():
    tick = Tick(_build_listing(), _build_point_in_time(), _build_tick_state())

    assert hasattr(tick.tick_state, "quotation_values")


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_ticks_compare_equal_when_composed_values_are_equal():
    listing = _build_listing()
    tick_state = _build_tick_state()

    left = Tick(listing, PointInTime("2026-08-17T09:30:00Z"), tick_state)
    right = Tick(listing, PointInTime("2026-08-17T14:30:00+05:00"), tick_state)

    assert left == right


def test_different_point_observation_meaning_does_not_compare_equal():
    listing = _build_listing()
    point_in_time = _build_point_in_time()

    left = Tick(listing, point_in_time, TickState((Price("100", Currency("USD")),)))
    right = Tick(listing, point_in_time, TickState((Price("101", Currency("USD")),)))

    assert left != right


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_ticks_have_equal_hashes():
    listing = _build_listing()
    tick_state = _build_tick_state()

    left = Tick(listing, PointInTime("2026-08-17T09:30:00Z"), tick_state)
    right = Tick(listing, PointInTime("2026-08-17T14:30:00+05:00"), tick_state)

    assert hash(left) == hash(right)


def test_tick_is_usable_as_dictionary_key():
    listing = _build_listing()
    key = Tick(listing, PointInTime("2026-08-17T09:30:00Z"), _build_tick_state())
    index = {key: "observation"}

    probe = Tick(
        listing,
        PointInTime("2026-08-17T14:30:00+05:00"),
        _build_tick_state(),
    )

    assert index[probe] == "observation"


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_concise_deterministic_business_representation():
    tick = Tick(_build_listing(), _build_point_in_time(), _build_tick_state())

    assert str(tick) == "AAPL@NASDAQ 2026-08-17T09:30:00Z 100 USD"


def test_repr_contains_tick_and_composed_components():
    tick = Tick(_build_listing(), _build_point_in_time(), _build_tick_state())
    representation = repr(tick)

    assert "Tick(" in representation
    assert "Listing(" in representation
    assert "PointInTime(" in representation
    assert "TickState(" in representation


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_tick_is_immutable():
    tick = Tick(_build_listing(), _build_point_in_time(), _build_tick_state())

    with pytest.raises(AttributeError):
        tick.point_in_time = PointInTime("2026-08-17T09:30:01Z")


def test_tick_does_not_support_ordering():
    left = Tick(
        _build_listing(),
        PointInTime("2026-08-17T09:30:00Z"),
        _build_tick_state(),
    )
    right = Tick(
        _build_listing(),
        PointInTime("2026-08-17T09:30:01Z"),
        _build_tick_state(),
    )

    with pytest.raises(TypeError):
        _ = left < right


def test_aggregate_ownership_is_preserved():
    listing = _build_listing()
    point_in_time = _build_point_in_time()
    tick_state = _build_tick_state()

    tick = Tick(listing, point_in_time, tick_state)

    assert tick.listing is listing
    assert tick.point_in_time is point_in_time
    assert tick.tick_state is tick_state


def test_composed_objects_remain_unchanged_by_tick_construction():
    listing = _build_listing()
    point_in_time = _build_point_in_time()
    tick_state = _build_tick_state()

    listing_repr_before = repr(listing)
    point_in_time_value_before = point_in_time.value
    tick_state_repr_before = repr(tick_state)

    _ = Tick(listing, point_in_time, tick_state)

    assert repr(listing) == listing_repr_before
    assert point_in_time.value == point_in_time_value_before
    assert repr(tick_state) == tick_state_repr_before
