"""Tests for the economic underlying reference."""

from __future__ import annotations

import pytest

from northstar_core.derivatives import InvalidUnderlyingReferenceError, UnderlyingReference
from northstar_core.foundation.exceptions.validation import ValidationError

# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["SP500", "WTI", "GOLD", "NIFTY50", "US10Y", "BRENT"])
def test_canonical_underlyings_are_preserved(value: str) -> None:
    assert UnderlyingReference(value).value == value


def test_the_value_is_uppercased() -> None:
    assert UnderlyingReference("sp500").value == "SP500"
    assert UnderlyingReference("Wti").value == "WTI"


def test_surrounding_whitespace_is_trimmed() -> None:
    assert UnderlyingReference("  SP500  ").value == "SP500"
    assert UnderlyingReference("\tGOLD\n").value == "GOLD"


def test_underscores_are_permitted() -> None:
    assert UnderlyingReference("US_10Y").value == "US_10Y"


def test_the_longest_permitted_value_is_accepted() -> None:
    assert UnderlyingReference("A" * 32).value == "A" * 32


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_none_is_rejected() -> None:
    with pytest.raises(InvalidUnderlyingReferenceError, match="cannot be None"):
        UnderlyingReference(None)


@pytest.mark.parametrize("value", [500, 1.5, True, b"SP500", ["SP500"], {"u": "SP500"}])
def test_non_string_values_are_rejected(value: object) -> None:
    with pytest.raises(InvalidUnderlyingReferenceError, match="must be a string"):
        UnderlyingReference(value)


@pytest.mark.parametrize("value", ["", "   ", "\t", "\n", " \t\n "])
def test_empty_and_blank_values_are_rejected(value: str) -> None:
    with pytest.raises(InvalidUnderlyingReferenceError, match="cannot be empty"):
        UnderlyingReference(value)


def test_an_over_length_value_is_rejected() -> None:
    with pytest.raises(InvalidUnderlyingReferenceError, match="exceeds maximum length"):
        UnderlyingReference("A" * 33)


@pytest.mark.parametrize(
    "value", ["SP 500", "S&P500", "SP-500", "SP.500", "WTI/CRUDE", "GOLD!", "NIFTY#50"]
)
def test_disallowed_characters_are_rejected(value: str) -> None:
    """The vocabulary is a canonical domain code, not a provider's formatting."""
    with pytest.raises(InvalidUnderlyingReferenceError, match="only uppercase letters"):
        UnderlyingReference(value)


def test_interior_whitespace_is_rejected_rather_than_stripped() -> None:
    with pytest.raises(InvalidUnderlyingReferenceError, match="only uppercase letters"):
        UnderlyingReference("SP 500")


def test_the_error_is_a_validation_error() -> None:
    assert issubclass(InvalidUnderlyingReferenceError, ValidationError)
    with pytest.raises(ValidationError):
        UnderlyingReference("")


# ---------------------------------------------------------------------------
# Value semantics and ordering
# ---------------------------------------------------------------------------


def test_equality_is_by_value_after_normalization() -> None:
    assert UnderlyingReference("SP500") == UnderlyingReference("  sp500  ")
    assert UnderlyingReference("SP500") != UnderlyingReference("WTI")


def test_hashing_follows_equality() -> None:
    assert hash(UnderlyingReference("SP500")) == hash(UnderlyingReference(" sp500 "))
    assert len({UnderlyingReference("SP500"), UnderlyingReference("sp500")}) == 1


def test_underlyings_order_deterministically() -> None:
    assert UnderlyingReference("GOLD") < UnderlyingReference("SP500")
    assert sorted(
        [
            UnderlyingReference("WTI"),
            UnderlyingReference("GOLD"),
            UnderlyingReference("SP500"),
        ]
    ) == [
        UnderlyingReference("GOLD"),
        UnderlyingReference("SP500"),
        UnderlyingReference("WTI"),
    ]


def test_the_value_is_immutable() -> None:
    underlying = UnderlyingReference("SP500")

    with pytest.raises(AttributeError):
        underlying.value = "WTI"


def test_it_is_usable_as_a_dictionary_key() -> None:
    assert {UnderlyingReference("SP500"): "index"}[UnderlyingReference("sp500")] == "index"


def test_string_and_repr_forms() -> None:
    underlying = UnderlyingReference("SP500")

    assert str(underlying) == "SP500"
    assert repr(underlying) == "UnderlyingReference(value='SP500')"


def test_it_carries_no_listing_or_product_meaning() -> None:
    """An underlying is often unlisted, and is never a product."""
    underlying = UnderlyingReference("SP500")

    for absent in ("listing_reference", "symbol", "exchange_code", "product_code", "currency"):
        assert not hasattr(underlying, absent)
