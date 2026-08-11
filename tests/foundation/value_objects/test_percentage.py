"""Reference test suite for the Percentage value object.

This suite defines the Northstar Value Object Testing Standard v1.0.
Future value object tests should follow this structure.
"""

from decimal import Decimal

import pytest

from northstar_core.foundation.exceptions.validation import (
    InvalidPercentageError,
    ValidationError,
)
from northstar_core.foundation.value_objects import Percentage

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_percentage_from_decimal():
    percentage = Percentage(Decimal("12.5"))

    assert percentage.value == Decimal("12.5")


def test_creates_valid_percentage_from_int():
    percentage = Percentage(100)

    assert percentage.value == Decimal("100")


def test_creates_valid_percentage_from_str():
    percentage = Percentage("12.5")

    assert percentage.value == Decimal("12.5")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none():
    with pytest.raises(InvalidPercentageError, match="Percentage cannot be None"):
        Percentage(None)


def test_rejects_empty_string():
    with pytest.raises(InvalidPercentageError, match="Percentage cannot be empty"):
        Percentage("")


def test_rejects_whitespace_only():
    with pytest.raises(InvalidPercentageError, match="Percentage cannot be empty"):
        Percentage("   ")


def test_rejects_float():
    with pytest.raises(InvalidPercentageError, match="Percentage must not be a float"):
        Percentage(12.5)


def test_rejects_non_numeric_value():
    with pytest.raises(InvalidPercentageError, match="Percentage must be a numeric value"):
        Percentage("abc")


def test_rejects_nan():
    with pytest.raises(InvalidPercentageError, match="Percentage must be finite"):
        Percentage(Decimal("NaN"))


def test_rejects_infinity():
    with pytest.raises(InvalidPercentageError, match="Percentage must be finite"):
        Percentage(Decimal("Infinity"))


def test_invalid_percentage_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        Percentage("")


def test_invalid_percentage_error_is_a_value_error():
    with pytest.raises(ValueError):
        Percentage("")


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_trims_leading_whitespace():
    percentage = Percentage("  12.5")

    assert percentage.value == Decimal("12.5")


def test_trims_trailing_whitespace():
    percentage = Percentage("12.5  ")

    assert percentage.value == Decimal("12.5")


def test_trims_leading_and_trailing_whitespace():
    percentage = Percentage("  12.5  ")

    assert percentage.value == Decimal("12.5")


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_percentages_compare_equal():
    assert Percentage("12.5") == Percentage(Decimal("12.5"))


def test_normalized_inputs_that_are_equivalent_compare_equal():
    assert Percentage("12.5000") == Percentage("12.5")


def test_different_percentages_are_not_equal():
    assert Percentage("12.5") != Percentage("15.0")


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_percentages_have_equal_hash():
    assert hash(Percentage("12.5000")) == hash(Percentage("12.5"))


def test_percentage_is_usable_as_dictionary_key():
    index = {Percentage("12.5"): "value"}

    assert index[Percentage("12.5000")] == "value"


def test_percentage_is_usable_in_a_set():
    percentages = {Percentage("12.5"), Percentage("12.5000"), Percentage("15")}

    assert len(percentages) == 2


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_percentage_orders_numerically():
    assert Percentage("12.5") < Percentage("15.0")


def test_percentage_ordering_is_consistent_with_equality():
    a = Percentage("12.5")
    b = Percentage("12.5000")

    assert not (a < b)
    assert not (a > b)


def test_sorted_percentages_produce_numeric_order():
    percentages = [Percentage("15"), Percentage("12.5"), Percentage("100")]

    assert sorted(percentages) == [Percentage("12.5"), Percentage("15"), Percentage("100")]


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_the_canonical_value():
    assert str(Percentage("12.5000")) == "12.5"


def test_repr_contains_class_name_and_value():
    assert repr(Percentage("12.5")) == "Percentage(value=Decimal('12.5'))"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_negative_percentage_is_valid():
    percentage = Percentage("-25")

    assert percentage.value == Decimal("-25")


def test_zero_percentage_is_valid():
    percentage = Percentage("0")

    assert percentage.value == Decimal("0")


def test_percentage_greater_than_hundred_is_valid():
    percentage = Percentage("150")

    assert percentage.value == Decimal("150")


def test_large_percentage_is_valid():
    percentage = Percentage("100000000000000")

    assert percentage.value == Decimal("100000000000000")


def test_boolean_is_rejected():
    with pytest.raises(InvalidPercentageError, match="Percentage must be a numeric value"):
        Percentage(True)


def test_percentage_semantics_use_percentage_units_directly():
    percentage = Percentage("12.5")

    assert percentage.value == Decimal("12.5")
    assert percentage.value != Decimal("0.125")


def test_percentage_is_immutable():
    percentage = Percentage("12.5")

    with pytest.raises(AttributeError):
        percentage.value = Decimal("15.0")


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------


def test_addition_returns_percentage():
    result = Percentage("12.5") + Percentage("2.5")

    assert result == Percentage("15")


def test_subtraction_returns_percentage():
    result = Percentage("12.5") - Percentage("37.5")

    assert result == Percentage("-25")


def test_multiplication_by_decimal_returns_percentage():
    result = Percentage("12.5") * Decimal("2")

    assert result == Percentage("25")


def test_division_by_decimal_returns_percentage():
    result = Percentage("12.5") / Decimal("2")

    assert result == Percentage("6.25")


def test_division_by_zero_rejected():
    with pytest.raises(InvalidPercentageError, match="Percentage cannot be divided by zero"):
        Percentage("12.5") / Decimal("0")


def test_multiplication_by_percentage_raises_type_error():
    with pytest.raises(TypeError):
        Percentage("12.5") * Percentage("2")


def test_division_by_percentage_raises_type_error():
    with pytest.raises(TypeError):
        Percentage("12.5") / Percentage("2")


# ---------------------------------------------------------------------------
# Canonical Decimal
# ---------------------------------------------------------------------------


def test_canonical_decimal_removes_trailing_zero_from_whole_value():
    percentage = Percentage(Decimal("1.0"))

    assert percentage.value == Decimal("1")
    assert str(percentage) == "1"


def test_canonical_decimal_removes_insignificant_trailing_zeros():
    percentage = Percentage(Decimal("12.5000"))

    assert percentage.value == Decimal("12.5")
    assert str(percentage) == "12.5"


def test_canonical_decimal_preserves_non_scientific_notation_for_ordinary_values():
    percentage = Percentage(Decimal("1000"))

    assert percentage.value == Decimal("1000")
    assert str(percentage) == "1000"
    assert "E" not in str(percentage)


def test_canonical_decimal_normalization_preserves_value_equality():
    assert Percentage(Decimal("1000.000")) == Percentage("1000")
