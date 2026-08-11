"""Reference test suite for the Quantity value object.

This suite defines the Northstar Value Object Testing Standard v1.0.
Future value object tests should follow this structure.
"""

from decimal import Decimal

import pytest

from northstar_core.foundation.exceptions.validation import (
    InvalidQuantityError,
    ValidationError,
)
from northstar_core.foundation.value_objects import Quantity

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_quantity_from_decimal():
    quantity = Quantity(Decimal("10.5"))

    assert quantity.value == Decimal("10.5")


def test_creates_valid_quantity_from_int():
    quantity = Quantity(10)

    assert quantity.value == Decimal("10")


def test_creates_valid_quantity_from_str():
    quantity = Quantity("10.5")

    assert quantity.value == Decimal("10.5")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none():
    with pytest.raises(InvalidQuantityError, match="Quantity cannot be None"):
        Quantity(None)


def test_rejects_empty_string():
    with pytest.raises(InvalidQuantityError, match="Quantity cannot be empty"):
        Quantity("")


def test_rejects_whitespace_only():
    with pytest.raises(InvalidQuantityError, match="Quantity cannot be empty"):
        Quantity("   ")


def test_rejects_float():
    with pytest.raises(InvalidQuantityError, match="Quantity must not be a float"):
        Quantity(10.5)


def test_rejects_non_numeric_value():
    with pytest.raises(InvalidQuantityError, match="Quantity must be a numeric value"):
        Quantity("abc")


def test_rejects_nan():
    with pytest.raises(InvalidQuantityError, match="Quantity must be finite"):
        Quantity(Decimal("NaN"))


def test_rejects_infinity():
    with pytest.raises(InvalidQuantityError, match="Quantity must be finite"):
        Quantity(Decimal("Infinity"))


def test_rejects_negative_quantity():
    with pytest.raises(InvalidQuantityError, match="Quantity cannot be negative"):
        Quantity("-1")


def test_invalid_quantity_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        Quantity("")


def test_invalid_quantity_error_is_a_value_error():
    with pytest.raises(ValueError):
        Quantity("")


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_trims_leading_whitespace():
    quantity = Quantity("  10.5")

    assert quantity.value == Decimal("10.5")


def test_trims_trailing_whitespace():
    quantity = Quantity("10.5  ")

    assert quantity.value == Decimal("10.5")


def test_trims_leading_and_trailing_whitespace():
    quantity = Quantity("  10.5  ")

    assert quantity.value == Decimal("10.5")


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_quantities_compare_equal():
    assert Quantity("1.5") == Quantity(Decimal("1.5"))


def test_normalized_inputs_that_are_equivalent_compare_equal():
    assert Quantity("1.5000") == Quantity("1.5")


def test_different_quantities_are_not_equal():
    assert Quantity("1.5") != Quantity("2.0")


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_quantities_have_equal_hash():
    assert hash(Quantity("1.5000")) == hash(Quantity("1.5"))


def test_quantity_is_usable_as_dictionary_key():
    index = {Quantity("1.5"): "value"}

    assert index[Quantity("1.5000")] == "value"


def test_quantity_is_usable_in_a_set():
    quantities = {Quantity("1.5"), Quantity("1.5000"), Quantity("2")}

    assert len(quantities) == 2


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_quantity_orders_numerically():
    assert Quantity("1.5") < Quantity("2.0")


def test_quantity_ordering_is_consistent_with_equality():
    a = Quantity("1.5")
    b = Quantity("1.5000")

    assert not (a < b)
    assert not (a > b)


def test_sorted_quantities_produce_numeric_order():
    quantities = [Quantity("2"), Quantity("1.5"), Quantity("10")]

    assert sorted(quantities) == [Quantity("1.5"), Quantity("2"), Quantity("10")]


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_the_canonical_value():
    assert str(Quantity("1.5000")) == "1.5"


def test_repr_contains_class_name_and_value():
    assert repr(Quantity("1.5")) == "Quantity(value=Decimal('1.5'))"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_zero_quantity_is_valid():
    quantity = Quantity("0")

    assert quantity.value == Decimal("0")


def test_large_quantity_is_valid():
    quantity = Quantity("10000000000000000000000")

    assert quantity.value == Decimal("10000000000000000000000")


def test_boolean_is_rejected():
    with pytest.raises(InvalidQuantityError, match="Quantity must be a numeric value"):
        Quantity(True)


def test_quantity_is_immutable():
    quantity = Quantity("1.5")

    with pytest.raises(AttributeError):
        quantity.value = Decimal("2.0")


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------


def test_addition_returns_quantity():
    result = Quantity("1.5") + Quantity("2.5")

    assert result == Quantity("4")


def test_subtraction_returns_quantity():
    result = Quantity("5") - Quantity("2")

    assert result == Quantity("3")


def test_subtraction_rejects_negative_result():
    with pytest.raises(InvalidQuantityError, match="Quantity cannot be negative"):
        Quantity("2") - Quantity("5")


def test_multiplication_by_decimal_returns_quantity():
    result = Quantity("2") * Decimal("1.5")

    assert result == Quantity("3")


def test_division_by_decimal_returns_quantity():
    result = Quantity("3") / Decimal("1.5")

    assert result == Quantity("2")


def test_division_by_zero_rejected():
    with pytest.raises(InvalidQuantityError, match="Quantity cannot be divided by zero"):
        Quantity("3") / Decimal("0")


def test_multiplication_by_quantity_raises_type_error():
    with pytest.raises(TypeError):
        Quantity("2") * Quantity("3")


def test_division_by_quantity_raises_type_error():
    with pytest.raises(TypeError):
        Quantity("6") / Quantity("3")


# ---------------------------------------------------------------------------
# Canonical Decimal
# ---------------------------------------------------------------------------


def test_canonical_decimal_removes_trailing_zero_from_whole_value():
    quantity = Quantity(Decimal("1.0"))

    assert quantity.value == Decimal("1")
    assert str(quantity) == "1"


def test_canonical_decimal_removes_insignificant_trailing_zeros():
    quantity = Quantity(Decimal("1.5000"))

    assert quantity.value == Decimal("1.5")
    assert str(quantity) == "1.5"


def test_canonical_decimal_preserves_non_scientific_notation_for_ordinary_values():
    quantity = Quantity(Decimal("1000"))

    assert quantity.value == Decimal("1000")
    assert str(quantity) == "1000"
    assert "E" not in str(quantity)


def test_canonical_decimal_normalization_preserves_value_equality():
    assert Quantity(Decimal("1000.000")) == Quantity("1000")
