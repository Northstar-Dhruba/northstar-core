"""Reference test suite for the Timeframe value object.

This suite defines the Northstar Value Object Testing Standard v1.0.
Future value object tests should follow this structure.
"""

import pytest

from northstar_core.foundation.exceptions.validation import (
    InvalidTimeframeError,
    ValidationError,
)
from northstar_core.foundation.value_objects import Timeframe

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_timeframe():
    timeframe = Timeframe("1m")

    assert timeframe.value == "1m"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none():
    with pytest.raises(InvalidTimeframeError, match="Timeframe cannot be None"):
        Timeframe(None)


def test_rejects_empty_string():
    with pytest.raises(InvalidTimeframeError, match="Timeframe cannot be empty"):
        Timeframe("")


def test_rejects_whitespace_only():
    with pytest.raises(InvalidTimeframeError, match="Timeframe cannot be empty"):
        Timeframe("   ")


def test_rejects_unsupported_label():
    with pytest.raises(
        InvalidTimeframeError,
        match="Timeframe is not part of the approved vocabulary",
    ):
        Timeframe("2h")


def test_rejects_malformed_label():
    with pytest.raises(
        InvalidTimeframeError,
        match="Timeframe is not part of the approved vocabulary",
    ):
        Timeframe("1mm")


def test_rejects_timestamp_value():
    with pytest.raises(
        InvalidTimeframeError,
        match="Timeframe is not part of the approved vocabulary",
    ):
        Timeframe("2026-08-15T12:30:00Z")


def test_rejects_date_value():
    with pytest.raises(
        InvalidTimeframeError,
        match="Timeframe is not part of the approved vocabulary",
    ):
        Timeframe("2026-08-15")


def test_rejects_timezone_identifier():
    with pytest.raises(
        InvalidTimeframeError,
        match="Timeframe is not part of the approved vocabulary",
    ):
        Timeframe("UTC")


def test_rejects_arbitrary_duration_string():
    with pytest.raises(
        InvalidTimeframeError,
        match="Timeframe is not part of the approved vocabulary",
    ):
        Timeframe("10m")


def test_invalid_timeframe_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        Timeframe("")


def test_invalid_timeframe_error_is_a_value_error():
    with pytest.raises(ValueError):
        Timeframe("")


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_trims_leading_whitespace():
    timeframe = Timeframe("  1m")

    assert timeframe.value == "1m"


def test_trims_trailing_whitespace():
    timeframe = Timeframe("1m  ")

    assert timeframe.value == "1m"


def test_trims_leading_and_trailing_whitespace():
    timeframe = Timeframe("  1m  ")

    assert timeframe.value == "1m"


def test_preserves_canonical_minute_label():
    timeframe = Timeframe("1m")

    assert timeframe.value == "1m"


def test_preserves_canonical_month_label():
    timeframe = Timeframe("1M")

    assert timeframe.value == "1M"


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_timeframes_compare_equal():
    assert Timeframe("1m") == Timeframe("1m")


def test_normalized_inputs_that_are_equivalent_compare_equal():
    assert Timeframe(" 1m ") == Timeframe("1m")


def test_different_timeframes_are_not_equal():
    assert Timeframe("1m") != Timeframe("5m")


def test_minute_and_month_timeframes_are_not_equal():
    assert Timeframe("1m") != Timeframe("1M")


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_timeframes_have_equal_hash():
    assert hash(Timeframe("1m")) == hash(Timeframe("1m"))


def test_different_timeframes_have_different_hashes():
    assert hash(Timeframe("1m")) != hash(Timeframe("1M"))


def test_timeframe_is_usable_as_dictionary_key():
    index = {Timeframe("1m"): "minute"}

    assert index[Timeframe(" 1m ")] == "minute"


def test_timeframe_is_usable_in_a_set():
    timeframes = {Timeframe("1m"), Timeframe(" 1m "), Timeframe("1M")}

    assert len(timeframes) == 2


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_timeframe_orders_lexically():
    assert Timeframe("1d") < Timeframe("1h")


def test_timeframe_ordering_is_consistent_with_equality():
    a = Timeframe("1m")
    b = Timeframe("1m")

    assert not (a < b)
    assert not (a > b)


def test_sorted_timeframes_produce_lexical_order():
    timeframes = [Timeframe("1w"), Timeframe("1h"), Timeframe("1d")]

    assert sorted(timeframes) == [Timeframe("1d"), Timeframe("1h"), Timeframe("1w")]


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_the_canonical_value():
    assert str(Timeframe("1m")) == "1m"


def test_repr_contains_class_name_and_value():
    assert repr(Timeframe("1m")) == "Timeframe(value='1m')"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_minute_timeframe_is_accepted():
    timeframe = Timeframe("1m")

    assert timeframe.value == "1m"


def test_five_minute_timeframe_is_accepted():
    timeframe = Timeframe("5m")

    assert timeframe.value == "5m"


def test_fifteen_minute_timeframe_is_accepted():
    timeframe = Timeframe("15m")

    assert timeframe.value == "15m"


def test_thirty_minute_timeframe_is_accepted():
    timeframe = Timeframe("30m")

    assert timeframe.value == "30m"


def test_one_hour_timeframe_is_accepted():
    timeframe = Timeframe("1h")

    assert timeframe.value == "1h"


def test_four_hour_timeframe_is_accepted():
    timeframe = Timeframe("4h")

    assert timeframe.value == "4h"


def test_one_day_timeframe_is_accepted():
    timeframe = Timeframe("1d")

    assert timeframe.value == "1d"


def test_one_week_timeframe_is_accepted():
    timeframe = Timeframe("1w")

    assert timeframe.value == "1w"


def test_one_month_timeframe_is_accepted():
    timeframe = Timeframe("1M")

    assert timeframe.value == "1M"


def test_one_year_timeframe_is_accepted():
    timeframe = Timeframe("1Y")

    assert timeframe.value == "1Y"


def test_unapproved_six_month_timeframe_is_rejected():
    with pytest.raises(
        InvalidTimeframeError,
        match="Timeframe is not part of the approved vocabulary",
    ):
        Timeframe("6M")


def test_timeframe_is_immutable():
    timeframe = Timeframe("1m")

    with pytest.raises(AttributeError):
        timeframe.value = "5m"
