"""Reference test suite for the Price value object.

This suite defines the Northstar composed value object contract for Price.
"""

from decimal import Decimal

import pytest

from northstar_core.foundation.exceptions.validation import (
    CurrencyMismatchError,
    InvalidCurrencyError,
    InvalidPriceError,
    ValidationError,
)
from northstar_core.foundation.value_objects import Currency, Price

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_price_from_decimal():
    price = Price(Decimal("100.00"), Currency("USD"))

    assert price.amount == Decimal("100")
    assert price.currency == Currency("USD")


def test_creates_valid_price_from_int():
    price = Price(100, Currency("USD"))

    assert price.amount == Decimal("100")
    assert price.currency == Currency("USD")


def test_creates_valid_price_from_str():
    price = Price("100.00", Currency("USD"))

    assert price.amount == Decimal("100")
    assert price.currency == Currency("USD")


def test_constructor_normalizes_decimal_amount_to_canonical_value():
    price = Price(Decimal("100.000"), Currency("USD"))

    assert price.amount == Decimal("100")


def test_rejects_missing_amount():
    with pytest.raises(InvalidPriceError, match="Price amount cannot be None"):
        Price(None, Currency("USD"))


def test_rejects_float_amount():
    with pytest.raises(InvalidPriceError, match="Price amount must not be a float"):
        Price(100.0, Currency("USD"))


def test_rejects_missing_currency():
    with pytest.raises(InvalidPriceError, match="Price currency cannot be None"):
        Price(Decimal("100"), None)


def test_rejects_invalid_currency_value_object():
    with pytest.raises(InvalidPriceError, match="Price currency must be a Currency value"):
        Price(Decimal("100"), "USD")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_negative_amount():
    with pytest.raises(InvalidPriceError, match="Price amount cannot be negative"):
        Price("-1", Currency("USD"))


def test_rejects_invalid_currency_structurally():
    with pytest.raises(InvalidCurrencyError, match="Currency contains invalid characters"):
        Currency("USD!")


def test_invalid_price_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        Price("-1", Currency("USD"))


def test_invalid_price_error_is_a_value_error():
    with pytest.raises(ValueError):
        Price("-1", Currency("USD"))


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_trims_leading_and_trailing_whitespace():
    price = Price("  100.00  ", Currency("USD"))

    assert price.amount == Decimal("100")


def test_normalizes_decimal_amount_to_canonical_value():
    price = Price("1.5000", Currency("USD"))

    assert price.amount == Decimal("1.5")


def test_normalizes_integer_string_amount_to_canonical_value():
    price = Price("100", Currency("USD"))

    assert price.amount == Decimal("100")


def test_normalizes_zero_amount():
    price = Price("0", Currency("USD"))

    assert price.amount == Decimal("0")


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_prices_compare_equal():
    assert Price("100", Currency("USD")) == Price("100", Currency("USD"))


def test_equal_prices_with_equivalent_values_compare_equal():
    assert Price("100.00", Currency("USD")) == Price("100", Currency("USD"))


def test_different_amounts_are_not_equal():
    assert Price("100", Currency("USD")) != Price("50", Currency("USD"))


def test_different_currencies_are_not_equal():
    assert Price("100", Currency("USD")) != Price("100", Currency("EUR"))


def test_equality_does_not_raise_currency_mismatch_error():
    assert Price("100", Currency("USD")) == Price("100", Currency("USD"))
    assert Price("100", Currency("USD")) != Price("100", Currency("EUR"))


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_prices_have_equal_hash():
    assert hash(Price("100", Currency("USD"))) == hash(Price("100", Currency("USD")))


def test_prices_with_different_currencies_have_different_hashes():
    assert hash(Price("100", Currency("USD"))) != hash(Price("100", Currency("EUR")))


def test_price_is_usable_as_dictionary_key():
    index = {Price("100", Currency("USD")): "value"}

    assert index[Price("100.00", Currency("USD"))] == "value"


def test_price_is_usable_in_a_set():
    prices = {
        Price("100", Currency("USD")),
        Price("100.00", Currency("USD")),
        Price("50", Currency("USD")),
    }

    assert len(prices) == 2


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_price_orders_by_amount_within_currency():
    assert Price("50", Currency("USD")) < Price("100", Currency("USD"))


def test_price_ordering_is_consistent_with_equality():
    a = Price("100", Currency("USD"))
    b = Price("100", Currency("USD"))

    assert not (a < b)
    assert not (a > b)


def test_cross_currency_ordering_raises_currency_mismatch_error():
    left = Price("100", Currency("USD"))
    right = Price("100", Currency("EUR"))
    with pytest.raises(CurrencyMismatchError, match="Price currencies do not match"):
        _ = left < right


def test_sorted_prices_produce_ascending_order():
    prices = [
        Price("100", Currency("USD")),
        Price("50", Currency("USD")),
        Price("75", Currency("USD")),
    ]

    assert sorted(prices) == [
        Price("50", Currency("USD")),
        Price("75", Currency("USD")),
        Price("100", Currency("USD")),
    ]


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_the_canonical_value_and_currency():
    assert str(Price("100.00", Currency("USD"))) == "100 USD"


def test_repr_contains_class_name_amount_and_currency():
    assert (
        repr(Price("100.00", Currency("USD")))
        == "Price(amount=Decimal('100'), currency=Currency(value='USD'))"
    )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_minimum_amount_is_zero():
    price = Price("0", Currency("USD"))

    assert price.amount == Decimal("0")


def test_price_is_immutable():
    price = Price("100", Currency("USD"))

    with pytest.raises(AttributeError):
        price.amount = Decimal("200")


def test_price_currency_is_immutable():
    price = Price("100", Currency("USD"))

    with pytest.raises(AttributeError):
        price.currency = Currency("EUR")


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------


def test_adds_matching_currency_prices():
    assert Price("100", Currency("USD")) + Price("50", Currency("USD")) == Price(
        "150", Currency("USD")
    )


def test_subtracts_matching_currency_prices():
    assert Price("150", Currency("USD")) - Price("50", Currency("USD")) == Price(
        "100", Currency("USD")
    )


def test_addition_with_different_currencies_raises_currency_mismatch_error():
    with pytest.raises(CurrencyMismatchError, match="Price currencies do not match"):
        Price("100", Currency("USD")) + Price("100", Currency("EUR"))


def test_subtraction_with_different_currencies_raises_currency_mismatch_error():
    with pytest.raises(CurrencyMismatchError, match="Price currencies do not match"):
        Price("100", Currency("USD")) - Price("100", Currency("EUR"))


def test_multiplies_by_decimal():
    assert Price("100", Currency("USD")) * Decimal("2") == Price("200", Currency("USD"))


def test_multiplies_by_int():
    assert Price("100", Currency("USD")) * 2 == Price("200", Currency("USD"))


def test_divides_by_decimal():
    assert Price("100", Currency("USD")) / Decimal("2") == Price("50", Currency("USD"))


def test_divides_by_int():
    assert Price("100", Currency("USD")) / 2 == Price("50", Currency("USD"))


def test_division_by_zero_raises_invalid_price_error():
    with pytest.raises(InvalidPriceError, match="Price cannot be divided by zero"):
        Price("100", Currency("USD")) / Decimal("0")


def test_multiplication_by_price_raises_type_error():
    with pytest.raises(TypeError):
        Price("100", Currency("USD")) * Price("2", Currency("USD"))


def test_division_by_price_raises_type_error():
    with pytest.raises(TypeError):
        Price("100", Currency("USD")) / Price("2", Currency("USD"))
