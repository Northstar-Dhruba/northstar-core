"""Reference contract test suite for the OHLCBar market observation.

This suite defines the Northstar Reference Interval Market Observation contract
for OHLCBar.
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
    Timeframe,
)
from northstar_core.market_data import InvalidOHLCBarError, OHLCBar
from northstar_core.market_data.value_objects import BarState


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


def _build_timeframe() -> Timeframe:
    return Timeframe("1m")


def _build_bar_state() -> BarState:
    return BarState((Price("100", Currency("USD")),))


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_ohlc_bar_from_listing_point_in_time_timeframe_and_bar_state():
    listing = _build_listing()
    point_in_time = _build_point_in_time()
    timeframe = _build_timeframe()
    bar_state = _build_bar_state()

    ohlc_bar = OHLCBar(listing, point_in_time, timeframe, bar_state)

    assert ohlc_bar.listing is listing
    assert ohlc_bar.point_in_time == point_in_time
    assert ohlc_bar.timeframe == timeframe
    assert ohlc_bar.bar_state == bar_state


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none_listing():
    with pytest.raises(InvalidOHLCBarError, match="listing cannot be None"):
        OHLCBar(None, _build_point_in_time(), _build_timeframe(), _build_bar_state())


def test_rejects_none_point_in_time():
    with pytest.raises(InvalidOHLCBarError, match="point-in-time context cannot be None"):
        OHLCBar(_build_listing(), None, _build_timeframe(), _build_bar_state())


def test_rejects_none_timeframe():
    with pytest.raises(InvalidOHLCBarError, match="timeframe context cannot be None"):
        OHLCBar(_build_listing(), _build_point_in_time(), None, _build_bar_state())


def test_rejects_none_bar_state():
    with pytest.raises(InvalidOHLCBarError, match="bar state cannot be None"):
        OHLCBar(_build_listing(), _build_point_in_time(), _build_timeframe(), None)


def test_rejects_invalid_listing_type():
    with pytest.raises(InvalidOHLCBarError, match="listing must be a Listing"):
        OHLCBar("listing", _build_point_in_time(), _build_timeframe(), _build_bar_state())


def test_rejects_invalid_point_in_time_type():
    with pytest.raises(
        InvalidOHLCBarError,
        match="point-in-time context must be a PointInTime",
    ):
        OHLCBar(_build_listing(), "2026-08-17T09:30:00Z", _build_timeframe(), _build_bar_state())


def test_rejects_invalid_timeframe_type():
    with pytest.raises(InvalidOHLCBarError, match="timeframe context must be a Timeframe"):
        OHLCBar(_build_listing(), _build_point_in_time(), "1m", _build_bar_state())


def test_rejects_invalid_bar_state_type():
    with pytest.raises(InvalidOHLCBarError, match="bar state must be a BarState"):
        OHLCBar(_build_listing(), _build_point_in_time(), _build_timeframe(), "100 USD")


def test_invalid_ohlc_bar_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        OHLCBar(None, _build_point_in_time(), _build_timeframe(), _build_bar_state())


def test_invalid_ohlc_bar_error_is_a_value_error():
    with pytest.raises(ValueError):
        OHLCBar(None, _build_point_in_time(), _build_timeframe(), _build_bar_state())


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def test_ohlc_bar_composes_listing_point_in_time_timeframe_and_bar_state():
    listing = _build_listing()
    point_in_time = _build_point_in_time()
    timeframe = _build_timeframe()
    bar_state = _build_bar_state()

    ohlc_bar = OHLCBar(listing, point_in_time, timeframe, bar_state)

    assert isinstance(ohlc_bar.listing, Listing)
    assert isinstance(ohlc_bar.point_in_time, PointInTime)
    assert isinstance(ohlc_bar.timeframe, Timeframe)
    assert isinstance(ohlc_bar.bar_state, BarState)


def test_ohlc_bar_does_not_directly_own_instrument_exchange_or_workflow_objects():
    ohlc_bar = OHLCBar(
        _build_listing(), _build_point_in_time(), _build_timeframe(), _build_bar_state()
    )

    assert not hasattr(ohlc_bar, "instrument")
    assert not hasattr(ohlc_bar, "exchange")
    assert not hasattr(ohlc_bar, "listing_status")
    assert not hasattr(ohlc_bar, "tradability")
    assert not hasattr(ohlc_bar, "price")
    assert not hasattr(ohlc_bar, "money")
    assert not hasattr(ohlc_bar, "orders")
    assert not hasattr(ohlc_bar, "trades")
    assert not hasattr(ohlc_bar, "positions")
    assert not hasattr(ohlc_bar, "portfolio")


def test_bar_state_remains_owner_of_interval_observation_meaning():
    ohlc_bar = OHLCBar(
        _build_listing(), _build_point_in_time(), _build_timeframe(), _build_bar_state()
    )

    assert hasattr(ohlc_bar.bar_state, "quotation_values")


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_ohlc_bars_compare_equal_when_composed_values_are_equal():
    listing = _build_listing()
    timeframe = _build_timeframe()
    bar_state = _build_bar_state()

    left = OHLCBar(listing, PointInTime("2026-08-17T09:30:00Z"), timeframe, bar_state)
    right = OHLCBar(listing, PointInTime("2026-08-17T14:30:00+05:00"), timeframe, bar_state)

    assert left == right


def test_different_interval_observation_meaning_does_not_compare_equal():
    listing = _build_listing()
    point_in_time = _build_point_in_time()
    timeframe = _build_timeframe()

    left = OHLCBar(listing, point_in_time, timeframe, BarState((Price("100", Currency("USD")),)))
    right = OHLCBar(listing, point_in_time, timeframe, BarState((Price("101", Currency("USD")),)))

    assert left != right


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_ohlc_bars_have_equal_hashes():
    listing = _build_listing()
    timeframe = _build_timeframe()
    bar_state = _build_bar_state()

    left = OHLCBar(listing, PointInTime("2026-08-17T09:30:00Z"), timeframe, bar_state)
    right = OHLCBar(listing, PointInTime("2026-08-17T14:30:00+05:00"), timeframe, bar_state)

    assert hash(left) == hash(right)


def test_ohlc_bar_is_usable_as_dictionary_key():
    listing = _build_listing()
    key = OHLCBar(
        listing, PointInTime("2026-08-17T09:30:00Z"), _build_timeframe(), _build_bar_state()
    )
    index = {key: "interval-observation"}

    probe = OHLCBar(
        listing,
        PointInTime("2026-08-17T14:30:00+05:00"),
        _build_timeframe(),
        _build_bar_state(),
    )

    assert index[probe] == "interval-observation"


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_concise_deterministic_business_representation():
    ohlc_bar = OHLCBar(
        _build_listing(), _build_point_in_time(), _build_timeframe(), _build_bar_state()
    )

    assert str(ohlc_bar) == "AAPL@NASDAQ 2026-08-17T09:30:00Z 1m 100 USD"


def test_repr_contains_ohlc_bar_and_composed_components():
    ohlc_bar = OHLCBar(
        _build_listing(), _build_point_in_time(), _build_timeframe(), _build_bar_state()
    )
    representation = repr(ohlc_bar)

    assert "OHLCBar(" in representation
    assert "Listing(" in representation
    assert "PointInTime(" in representation
    assert "Timeframe(" in representation
    assert "BarState(" in representation


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_ohlc_bar_is_immutable():
    ohlc_bar = OHLCBar(
        _build_listing(), _build_point_in_time(), _build_timeframe(), _build_bar_state()
    )

    with pytest.raises(AttributeError):
        ohlc_bar.timeframe = Timeframe("5m")


def test_ohlc_bar_does_not_support_ordering():
    left = OHLCBar(
        _build_listing(),
        PointInTime("2026-08-17T09:30:00Z"),
        _build_timeframe(),
        _build_bar_state(),
    )
    right = OHLCBar(
        _build_listing(),
        PointInTime("2026-08-17T09:30:01Z"),
        _build_timeframe(),
        _build_bar_state(),
    )

    with pytest.raises(TypeError):
        _ = left < right


def test_aggregate_ownership_is_preserved():
    listing = _build_listing()
    point_in_time = _build_point_in_time()
    timeframe = _build_timeframe()
    bar_state = _build_bar_state()

    ohlc_bar = OHLCBar(listing, point_in_time, timeframe, bar_state)

    assert ohlc_bar.listing is listing
    assert ohlc_bar.point_in_time is point_in_time
    assert ohlc_bar.timeframe is timeframe
    assert ohlc_bar.bar_state is bar_state


def test_composed_objects_remain_unchanged_by_ohlc_bar_construction():
    listing = _build_listing()
    point_in_time = _build_point_in_time()
    timeframe = _build_timeframe()
    bar_state = _build_bar_state()

    listing_repr_before = repr(listing)
    point_in_time_value_before = point_in_time.value
    timeframe_value_before = timeframe.value
    bar_state_repr_before = repr(bar_state)

    _ = OHLCBar(listing, point_in_time, timeframe, bar_state)

    assert repr(listing) == listing_repr_before
    assert point_in_time.value == point_in_time_value_before
    assert timeframe.value == timeframe_value_before
    assert repr(bar_state) == bar_state_repr_before


def test_timeframe_composition_is_preserved():
    timeframe = _build_timeframe()
    ohlc_bar = OHLCBar(_build_listing(), _build_point_in_time(), timeframe, _build_bar_state())

    assert ohlc_bar.timeframe is timeframe
