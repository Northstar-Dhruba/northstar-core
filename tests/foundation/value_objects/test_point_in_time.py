"""Reference contract test suite for the PointInTime value object.

This suite defines the Northstar Foundation Value Object contract for
PointInTime.
"""

import pytest

from northstar_core.foundation.exceptions.validation import (
    InvalidPointInTimeError,
    ValidationError,
)
from northstar_core.foundation.value_objects import PointInTime, Timeframe

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_point_in_time_from_canonical_utc_representation():
    point_in_time = PointInTime("2026-08-17T09:30:00Z")

    assert point_in_time.value == "2026-08-17T09:30:00Z"


def test_creates_point_in_time_from_explicit_utc_offset():
    point_in_time = PointInTime("2026-08-17T14:30:00+05:00")

    assert point_in_time.value == "2026-08-17T09:30:00Z"


def test_creates_point_in_time_with_fractional_seconds():
    point_in_time = PointInTime("2026-08-17T09:30:00.125Z")

    assert point_in_time.value == "2026-08-17T09:30:00.125Z"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none():
    with pytest.raises(InvalidPointInTimeError, match="PointInTime cannot be None"):
        PointInTime(None)


def test_rejects_empty_string():
    with pytest.raises(InvalidPointInTimeError, match="PointInTime cannot be empty"):
        PointInTime("")


def test_rejects_date_only_value():
    with pytest.raises(InvalidPointInTimeError, match="complete date, time, and UTC offset"):
        PointInTime("2026-08-17")


def test_rejects_time_only_value():
    with pytest.raises(InvalidPointInTimeError, match="complete date, time, and UTC offset"):
        PointInTime("09:30:00Z")


def test_rejects_local_time_without_explicit_offset():
    with pytest.raises(InvalidPointInTimeError, match="complete date, time, and UTC offset"):
        PointInTime("2026-08-17T09:30:00")


def test_rejects_timeframe_value():
    with pytest.raises(InvalidPointInTimeError, match="complete date, time, and UTC offset"):
        PointInTime("1m")


def test_rejects_duration_value():
    with pytest.raises(InvalidPointInTimeError, match="complete date, time, and UTC offset"):
        PointInTime("PT1H")


def test_rejects_relative_expression():
    with pytest.raises(InvalidPointInTimeError, match="complete date, time, and UTC offset"):
        PointInTime("now")


def test_rejects_timezone_identifier():
    with pytest.raises(InvalidPointInTimeError, match="complete date, time, and UTC offset"):
        PointInTime("UTC")


def test_rejects_invalid_temporal_value():
    with pytest.raises(InvalidPointInTimeError, match="invalid temporal value"):
        PointInTime("2026-02-30T09:30:00Z")


def test_rejects_fractional_precision_beyond_canonical_precision():
    with pytest.raises(InvalidPointInTimeError, match="cannot exceed six decimal places"):
        PointInTime("2026-08-17T09:30:00.1234567Z")


def test_invalid_point_in_time_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        PointInTime(None)


def test_invalid_point_in_time_error_is_a_value_error():
    with pytest.raises(ValueError):
        PointInTime(None)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_trims_leading_and_trailing_whitespace():
    point_in_time = PointInTime("  2026-08-17T09:30:00Z  ")

    assert point_in_time.value == "2026-08-17T09:30:00Z"


def test_normalizes_explicit_offset_to_canonical_utc_representation():
    point_in_time = PointInTime("2026-08-17T14:30:00+05:00")

    assert point_in_time.value == "2026-08-17T09:30:00Z"


def test_removes_insignificant_fractional_second_zeroes():
    point_in_time = PointInTime("2026-08-17T09:30:00.120000Z")

    assert point_in_time.value == "2026-08-17T09:30:00.12Z"


def test_removes_fraction_when_fractional_seconds_are_zero():
    point_in_time = PointInTime("2026-08-17T09:30:00.000000Z")

    assert point_in_time.value == "2026-08-17T09:30:00Z"


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equivalent_temporal_representations_compare_equal():
    assert PointInTime("2026-08-17T14:30:00+05:00") == PointInTime("2026-08-17T09:30:00Z")


def test_different_temporal_locations_are_not_equal():
    assert PointInTime("2026-08-17T09:30:00Z") != PointInTime("2026-08-17T09:30:01Z")


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_point_in_time_values_have_equal_hashes():
    assert hash(PointInTime("2026-08-17T14:30:00+05:00")) == hash(
        PointInTime("2026-08-17T09:30:00Z")
    )


def test_point_in_time_is_usable_as_dictionary_key():
    index = {PointInTime("2026-08-17T09:30:00Z"): "observation"}

    assert index[PointInTime("2026-08-17T14:30:00+05:00")] == "observation"


def test_point_in_time_is_usable_in_a_set():
    points_in_time = {
        PointInTime("2026-08-17T09:30:00Z"),
        PointInTime("2026-08-17T14:30:00+05:00"),
        PointInTime("2026-08-17T09:30:01Z"),
    }

    assert len(points_in_time) == 2


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_the_canonical_value():
    assert str(PointInTime("2026-08-17T14:30:00+05:00")) == "2026-08-17T09:30:00Z"


def test_repr_contains_class_name_and_canonical_value():
    representation = repr(PointInTime("2026-08-17T14:30:00+05:00"))

    assert "PointInTime" in representation
    assert "2026-08-17T09:30:00Z" in representation


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_canonical_utc_representation_preserves_business_meaning():
    point_in_time = PointInTime("2026-08-17T14:30:00+05:00")

    assert point_in_time.value == "2026-08-17T09:30:00Z"


def test_point_in_time_remains_distinct_from_timeframe():
    point_in_time = PointInTime("2026-08-17T09:30:00Z")

    assert not isinstance(point_in_time, Timeframe)


def test_point_in_time_does_not_support_ordering():
    with pytest.raises(TypeError):
        _ = PointInTime("2026-08-17T09:30:00Z") < PointInTime("2026-08-17T09:30:01Z")


def test_point_in_time_is_immutable():
    point_in_time = PointInTime("2026-08-17T09:30:00Z")

    with pytest.raises(AttributeError):
        point_in_time.value = "2026-08-17T09:30:01Z"
