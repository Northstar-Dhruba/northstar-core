"""Tests for the derivative expiration calendar date."""

from __future__ import annotations

import pytest

from northstar_core.derivatives import ExpirationDate, InvalidExpirationDateError
from northstar_core.foundation.exceptions.validation import ValidationError

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_a_canonical_date_is_preserved() -> None:
    assert ExpirationDate("2026-03-20").value == "2026-03-20"


def test_surrounding_whitespace_is_normalized() -> None:
    assert ExpirationDate("  2026-03-20  ").value == "2026-03-20"
    assert ExpirationDate("\t2026-03-20\n").value == "2026-03-20"


@pytest.mark.parametrize(
    "value",
    ["2026-01-01", "2026-12-31", "2000-02-29", "2024-02-29", "1999-06-15", "2099-11-30"],
)
def test_real_calendar_dates_are_accepted(value: str) -> None:
    assert ExpirationDate(value).value == value


def test_leap_day_is_accepted_in_a_leap_year() -> None:
    assert ExpirationDate("2024-02-29").value == "2024-02-29"


def test_leap_day_is_rejected_in_a_common_year() -> None:
    with pytest.raises(InvalidExpirationDateError, match="must be a real calendar date"):
        ExpirationDate("2026-02-29")


def test_century_leap_rules_are_respected() -> None:
    """2000 is a leap year; 1900 is not."""
    assert ExpirationDate("2000-02-29").value == "2000-02-29"
    with pytest.raises(InvalidExpirationDateError, match="must be a real calendar date"):
        ExpirationDate("1900-02-29")


@pytest.mark.parametrize(
    "value",
    ["2026-04-31", "2026-06-31", "2026-09-31", "2026-11-31", "2026-02-30", "2026-13-01"],
)
def test_impossible_dates_are_rejected(value: str) -> None:
    with pytest.raises(InvalidExpirationDateError, match="must be a real calendar date"):
        ExpirationDate(value)


# ---------------------------------------------------------------------------
# Format validation
# ---------------------------------------------------------------------------


def test_none_is_rejected() -> None:
    with pytest.raises(InvalidExpirationDateError, match="cannot be None"):
        ExpirationDate(None)


@pytest.mark.parametrize("value", [20260320, 2026.03, True, ["2026-03-20"], {"y": 2026}])
def test_non_string_values_are_rejected(value: object) -> None:
    with pytest.raises(InvalidExpirationDateError, match="must be a string"):
        ExpirationDate(value)


@pytest.mark.parametrize("value", ["", "   ", "\t", "\n"])
def test_empty_values_are_rejected(value: str) -> None:
    with pytest.raises(InvalidExpirationDateError, match="cannot be empty"):
        ExpirationDate(value)


@pytest.mark.parametrize(
    "value",
    [
        "2026-3-20",
        "2026-03-2",
        "26-03-20",
        "2026/03/20",
        "20-03-2026",
        "2026-03",
        "2026",
        "March 2026",
        "2026-03-20-01",
    ],
)
def test_non_canonical_formats_are_rejected(value: str) -> None:
    with pytest.raises(InvalidExpirationDateError, match="must be a YYYY-MM-DD calendar date"):
        ExpirationDate(value)


def test_no_time_of_day_is_accepted() -> None:
    """An expiration is a date; an instant would invent a time that is not known."""
    with pytest.raises(InvalidExpirationDateError, match="must be a YYYY-MM-DD calendar date"):
        ExpirationDate("2026-03-20T16:00:00Z")


def test_no_timezone_is_accepted() -> None:
    with pytest.raises(InvalidExpirationDateError, match="must be a YYYY-MM-DD calendar date"):
        ExpirationDate("2026-03-20Z")


def test_the_error_is_a_validation_error() -> None:
    assert issubclass(InvalidExpirationDateError, ValidationError)
    with pytest.raises(ValidationError):
        ExpirationDate("not-a-date")


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_dates_order_chronologically() -> None:
    assert ExpirationDate("2026-03-20") < ExpirationDate("2026-06-19")
    assert ExpirationDate("2026-06-19") > ExpirationDate("2026-03-20")
    assert ExpirationDate("2026-03-20") <= ExpirationDate("2026-03-20")


def test_ordering_crosses_month_and_year_boundaries() -> None:
    ordered = [
        ExpirationDate("2025-12-31"),
        ExpirationDate("2026-01-01"),
        ExpirationDate("2026-09-30"),
        ExpirationDate("2026-10-01"),
        ExpirationDate("2027-01-01"),
    ]

    assert sorted(reversed(ordered)) == ordered


def test_zero_padding_makes_text_order_chronological() -> None:
    """The canonical form is fixed width, so string order is date order."""
    assert ExpirationDate("2026-09-30").value < ExpirationDate("2026-10-01").value
    assert ExpirationDate("2026-09-30") < ExpirationDate("2026-10-01")


def test_sorting_a_contract_series_is_deterministic() -> None:
    series = (
        ExpirationDate("2026-12-18"),
        ExpirationDate("2026-03-20"),
        ExpirationDate("2026-09-18"),
        ExpirationDate("2026-06-19"),
    )

    assert [entry.value for entry in sorted(series)] == [
        "2026-03-20",
        "2026-06-19",
        "2026-09-18",
        "2026-12-18",
    ]


# ---------------------------------------------------------------------------
# Value semantics
# ---------------------------------------------------------------------------


def test_equality_is_by_value() -> None:
    assert ExpirationDate("2026-03-20") == ExpirationDate("  2026-03-20  ")
    assert ExpirationDate("2026-03-20") != ExpirationDate("2026-03-21")


def test_hashing_follows_equality() -> None:
    assert hash(ExpirationDate("2026-03-20")) == hash(ExpirationDate(" 2026-03-20 "))
    assert len({ExpirationDate("2026-03-20"), ExpirationDate("2026-03-20")}) == 1


def test_the_value_is_immutable() -> None:
    expiration = ExpirationDate("2026-03-20")

    with pytest.raises(AttributeError):
        expiration.value = "2026-06-19"


def test_it_is_usable_as_a_dictionary_key() -> None:
    assert {ExpirationDate("2026-03-20"): "March"}[ExpirationDate("2026-03-20")] == "March"


def test_string_and_repr_forms() -> None:
    expiration = ExpirationDate("2026-03-20")

    assert str(expiration) == "2026-03-20"
    assert repr(expiration) == "ExpirationDate(value='2026-03-20')"


def test_it_exposes_no_instant_conversion() -> None:
    """Relating an expiry to an instant needs session knowledge this value lacks."""
    expiration = ExpirationDate("2026-03-20")

    for absent in ("to_point_in_time", "point_in_time", "as_instant", "compare", "timezone"):
        assert not hasattr(expiration, absent)
