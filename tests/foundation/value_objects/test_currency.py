"""Reference test suite for the Currency value object.

This suite defines the Northstar Value Object Testing Standard v1.0.
Future value object tests should follow this structure.
"""

import pytest

from northstar_core.foundation.exceptions.validation import (
    InvalidCurrencyError,
    ValidationError,
)
from northstar_core.foundation.value_objects import Currency

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_currency():
    currency = Currency("USD")

    assert currency.value == "USD"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none():
    with pytest.raises(InvalidCurrencyError, match="Currency cannot be None"):
        Currency(None)


def test_rejects_empty_string():
    with pytest.raises(InvalidCurrencyError, match="Currency cannot be empty"):
        Currency("")


def test_rejects_whitespace_only():
    with pytest.raises(InvalidCurrencyError, match="Currency cannot be empty"):
        Currency("   ")


def test_rejects_embedded_whitespace():
    with pytest.raises(InvalidCurrencyError, match="Currency contains whitespace"):
        Currency("US D")


def test_rejects_invalid_characters():
    with pytest.raises(InvalidCurrencyError, match="Currency contains invalid characters"):
        Currency("US$")


def test_rejects_currency_shorter_than_minimum_length():
    with pytest.raises(InvalidCurrencyError, match="Currency is too short"):
        Currency("US")


def test_rejects_currency_exceeding_maximum_length():
    with pytest.raises(InvalidCurrencyError, match="Currency exceeds maximum length"):
        Currency("USD123")


def test_invalid_currency_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        Currency("")


def test_invalid_currency_error_is_a_value_error():
    with pytest.raises(ValueError):
        Currency("")


def test_currency_validation_is_structural_not_registry_based():
    currency = Currency("ZZZZ")

    assert currency.value == "ZZZZ"


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_trims_leading_whitespace():
    currency = Currency("  USD")

    assert currency.value == "USD"


def test_trims_trailing_whitespace():
    currency = Currency("USD  ")

    assert currency.value == "USD"


def test_trims_leading_and_trailing_whitespace():
    currency = Currency("  USD  ")

    assert currency.value == "USD"


def test_normalizes_lowercase_to_uppercase():
    currency = Currency("usd")

    assert currency.value == "USD"


def test_normalizes_mixed_case_to_uppercase():
    currency = Currency("UsD")

    assert currency.value == "USD"


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_currencies_compare_equal():
    assert Currency("USD") == Currency("USD")


def test_normalized_inputs_that_are_equivalent_compare_equal():
    assert Currency("usd") == Currency("USD")


def test_different_currencies_are_not_equal():
    assert Currency("USD") != Currency("EUR")


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_currencies_have_equal_hash():
    assert hash(Currency("USD")) == hash(Currency("USD"))


def test_currency_is_usable_as_dictionary_key():
    index = {Currency("USD"): 100.0}

    assert index[Currency("usd")] == 100.0


def test_currency_is_usable_in_a_set():
    currencies = {Currency("USD"), Currency("usd"), Currency("EUR")}

    assert len(currencies) == 2


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_currency_orders_lexically():
    assert Currency("EUR") < Currency("USD")


def test_currency_ordering_is_consistent_with_equality():
    a = Currency("USD")
    b = Currency("USD")

    assert not (a < b)
    assert not (a > b)


def test_sorted_currencies_produce_lexical_order():
    currencies = [Currency("USD"), Currency("EUR"), Currency("JPY")]

    assert sorted(currencies) == [Currency("EUR"), Currency("JPY"), Currency("USD")]


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_the_canonical_value():
    assert str(Currency("USD")) == "USD"


def test_repr_contains_class_name_and_value():
    assert repr(Currency("USD")) == "Currency(value='USD')"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_minimum_length_currency():
    currency = Currency("ABC")

    assert currency.value == "ABC"


def test_maximum_length_currency():
    value = "ABCDE"
    currency = Currency(value)

    assert currency.value == value


def test_fiat_currency_codes_are_accepted():
    currency = Currency("JPY")

    assert currency.value == "JPY"


def test_digital_asset_codes_are_accepted():
    currency = Currency("USDT")

    assert currency.value == "USDT"


def test_structurally_valid_code_is_accepted_even_if_not_registry_recognized():
    currency = Currency("ABC")

    assert currency.value == "ABC"


def test_currency_is_immutable():
    currency = Currency("USD")

    with pytest.raises(AttributeError):
        currency.value = "EUR"
