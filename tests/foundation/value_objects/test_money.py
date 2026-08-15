"""Reference test suite for the Money value object.

This suite defines the Northstar composed value object contract for Money.
"""

from decimal import Decimal

import pytest

from northstar_core.foundation.exceptions.validation import (
    CurrencyMismatchError,
    InvalidCurrencyError,
    InvalidMoneyError,
    ValidationError,
)
from northstar_core.foundation.value_objects import Currency, Money

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_money_from_decimal():
    money = Money(Decimal("100.00"), Currency("USD"))

    assert money.amount == Decimal("100")
    assert money.currency == Currency("USD")


def test_creates_valid_money_from_int():
    money = Money(100, Currency("USD"))

    assert money.amount == Decimal("100")
    assert money.currency == Currency("USD")


def test_creates_valid_money_from_str():
    money = Money("100.00", Currency("USD"))

    assert money.amount == Decimal("100")
    assert money.currency == Currency("USD")


def test_constructor_normalizes_decimal_amount_to_canonical_value():
    money = Money(Decimal("100.000"), Currency("USD"))

    assert money.amount == Decimal("100")


def test_rejects_missing_amount():
    with pytest.raises(InvalidMoneyError, match="Money amount cannot be None"):
        Money(None, Currency("USD"))


def test_rejects_float_amount():
    with pytest.raises(InvalidMoneyError, match="Money amount must not be a float"):
        Money(100.0, Currency("USD"))


def test_rejects_missing_currency():
    with pytest.raises(InvalidMoneyError, match="Money currency cannot be None"):
        Money(Decimal("100"), None)


def test_rejects_invalid_currency_value_object():
    with pytest.raises(InvalidMoneyError, match="Money currency must be a Currency value"):
        Money(Decimal("100"), "USD")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_accepts_negative_amount():
    money = Money("-50.00", Currency("USD"))

    assert money.amount == Decimal("-50")


def test_rejects_invalid_currency_structurally():
    with pytest.raises(InvalidCurrencyError, match="Currency contains invalid characters"):
        Currency("USD!")


def test_invalid_money_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        Money(None, Currency("USD"))


def test_invalid_money_error_is_a_value_error():
    with pytest.raises(ValueError):
        Money(None, Currency("USD"))


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_trims_leading_and_trailing_whitespace():
    money = Money("  100.00  ", Currency("USD"))

    assert money.amount == Decimal("100")


def test_normalizes_decimal_amount_to_canonical_value():
    money = Money("-50.000", Currency("USD"))

    assert money.amount == Decimal("-50")


def test_normalizes_integer_string_amount_to_canonical_value():
    money = Money("100", Currency("USD"))

    assert money.amount == Decimal("100")


def test_normalizes_zero_amount():
    money = Money("0", Currency("USD"))

    assert money.amount == Decimal("0")


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_money_compare_equal():
    assert Money("100", Currency("USD")) == Money("100", Currency("USD"))


def test_equal_money_with_equivalent_values_compare_equal():
    assert Money("100.00", Currency("USD")) == Money("100", Currency("USD"))


def test_different_amounts_are_not_equal():
    assert Money("100", Currency("USD")) != Money("50", Currency("USD"))


def test_different_currencies_are_not_equal():
    assert Money("100", Currency("USD")) != Money("100", Currency("EUR"))


def test_equality_does_not_raise_currency_mismatch_error():
    assert Money("100", Currency("USD")) == Money("100", Currency("USD"))
    assert Money("100", Currency("USD")) != Money("100", Currency("EUR"))


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_money_have_equal_hash():
    assert hash(Money("100", Currency("USD"))) == hash(Money("100", Currency("USD")))


def test_money_with_different_currencies_have_different_hashes():
    assert hash(Money("100", Currency("USD"))) != hash(Money("100", Currency("EUR")))


def test_money_is_usable_as_dictionary_key():
    index = {Money("100", Currency("USD")): "value"}

    assert index[Money("100.00", Currency("USD"))] == "value"


def test_money_is_usable_in_a_set():
    money_values = {
        Money("100", Currency("USD")),
        Money("100.00", Currency("USD")),
        Money("50", Currency("USD")),
    }

    assert len(money_values) == 2


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_money_orders_by_amount_within_currency():
    assert Money("50", Currency("USD")) < Money("100", Currency("USD"))


def test_negative_money_orders_correctly_within_currency():
    assert Money("-50", Currency("USD")) < Money("0", Currency("USD"))


def test_money_ordering_is_consistent_with_equality():
    a = Money("100", Currency("USD"))
    b = Money("100", Currency("USD"))

    assert not (a < b)
    assert not (a > b)


def test_cross_currency_ordering_raises_currency_mismatch_error():
    left = Money("100", Currency("USD"))
    right = Money("100", Currency("EUR"))

    with pytest.raises(CurrencyMismatchError, match="Money currencies do not match"):
        _ = left < right


def test_sorted_money_produce_ascending_order():
    values = [
        Money("100", Currency("USD")),
        Money("-50", Currency("USD")),
        Money("75", Currency("USD")),
    ]

    assert sorted(values) == [
        Money("-50", Currency("USD")),
        Money("75", Currency("USD")),
        Money("100", Currency("USD")),
    ]


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_the_canonical_value_and_currency():
    assert str(Money("100.00", Currency("USD"))) == "100 USD"


def test_repr_contains_class_name_amount_and_currency():
    assert (
        repr(Money("100.00", Currency("USD")))
        == "Money(amount=Decimal('100'), currency=Currency(value='USD'))"
    )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_negative_zero_is_canonicalized_to_zero():
    money = Money("-0", Currency("USD"))

    assert money.amount == Decimal("0")


def test_money_is_immutable():
    money = Money("100", Currency("USD"))

    with pytest.raises(AttributeError):
        money.amount = Decimal("200")


def test_money_currency_is_immutable():
    money = Money("100", Currency("USD"))

    with pytest.raises(AttributeError):
        money.currency = Currency("EUR")


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------


def test_adds_matching_currency_money():
    assert Money("100", Currency("USD")) + Money("50", Currency("USD")) == Money(
        "150", Currency("USD")
    )


def test_subtracts_matching_currency_money():
    assert Money("100", Currency("USD")) - Money("150", Currency("USD")) == Money(
        "-50", Currency("USD")
    )


def test_adds_negative_value_money():
    assert Money("-50", Currency("USD")) + Money("100", Currency("USD")) == Money(
        "50", Currency("USD")
    )


def test_addition_with_different_currencies_raises_currency_mismatch_error():
    with pytest.raises(CurrencyMismatchError, match="Money currencies do not match"):
        Money("100", Currency("USD")) + Money("100", Currency("EUR"))


def test_subtraction_with_different_currencies_raises_currency_mismatch_error():
    with pytest.raises(CurrencyMismatchError, match="Money currencies do not match"):
        Money("100", Currency("USD")) - Money("100", Currency("EUR"))


def test_multiplies_by_decimal():
    assert Money("100", Currency("USD")) * Decimal("2") == Money("200", Currency("USD"))


def test_multiplies_by_int():
    assert Money("100", Currency("USD")) * 2 == Money("200", Currency("USD"))


def test_divides_by_decimal():
    assert Money("100", Currency("USD")) / Decimal("2") == Money("50", Currency("USD"))


def test_divides_by_int():
    assert Money("100", Currency("USD")) / 2 == Money("50", Currency("USD"))


def test_division_by_zero_raises_invalid_money_error():
    with pytest.raises(InvalidMoneyError, match="Money cannot be divided by zero"):
        Money("100", Currency("USD")) / Decimal("0")


def test_multiplication_by_money_raises_type_error():
    with pytest.raises(TypeError):
        Money("100", Currency("USD")) * Money("2", Currency("USD"))


def test_division_by_money_raises_type_error():
    with pytest.raises(TypeError):
        Money("100", Currency("USD")) / Money("2", Currency("USD"))
