"""Reference test suite for the ExchangeCode value object.

This suite defines the Northstar Value Object Testing Standard v1.0.
Future value object tests should follow this structure.
"""

import pytest

from northstar_core.foundation.exceptions.validation import (
    InvalidExchangeCodeError,
    ValidationError,
)
from northstar_core.foundation.value_objects import ExchangeCode

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_exchange_code():
    exchange_code = ExchangeCode("NYSE")

    assert exchange_code.value == "NYSE"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none():
    with pytest.raises(InvalidExchangeCodeError, match="ExchangeCode cannot be None"):
        ExchangeCode(None)


def test_rejects_empty_string():
    with pytest.raises(InvalidExchangeCodeError, match="ExchangeCode cannot be empty"):
        ExchangeCode("")


def test_rejects_whitespace_only():
    with pytest.raises(InvalidExchangeCodeError, match="ExchangeCode cannot be empty"):
        ExchangeCode("   ")


def test_rejects_embedded_whitespace():
    with pytest.raises(InvalidExchangeCodeError, match="ExchangeCode contains whitespace"):
        ExchangeCode("NYSE EX")


def test_rejects_invalid_characters():
    with pytest.raises(InvalidExchangeCodeError, match="ExchangeCode contains invalid characters"):
        ExchangeCode("NYSE!")


def test_rejects_exchange_code_exceeding_maximum_length():
    with pytest.raises(InvalidExchangeCodeError, match="ExchangeCode exceeds maximum length"):
        ExchangeCode("A" * 17)


def test_invalid_exchange_code_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        ExchangeCode("")


def test_invalid_exchange_code_error_is_a_value_error():
    with pytest.raises(ValueError):
        ExchangeCode("")


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_trims_leading_whitespace():
    exchange_code = ExchangeCode("  NYSE")

    assert exchange_code.value == "NYSE"


def test_trims_trailing_whitespace():
    exchange_code = ExchangeCode("NYSE  ")

    assert exchange_code.value == "NYSE"


def test_trims_leading_and_trailing_whitespace():
    exchange_code = ExchangeCode("  NYSE  ")

    assert exchange_code.value == "NYSE"


def test_normalizes_lowercase_to_uppercase():
    exchange_code = ExchangeCode("nyse")

    assert exchange_code.value == "NYSE"


def test_normalizes_mixed_case_to_uppercase():
    exchange_code = ExchangeCode("NySe")

    assert exchange_code.value == "NYSE"


def test_normalizes_inputs_with_surrounding_whitespace_compare_equal():
    assert ExchangeCode(" NYSE ") == ExchangeCode("NYSE")


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_exchange_codes_compare_equal():
    assert ExchangeCode("NYSE") == ExchangeCode("NYSE")


def test_normalized_inputs_that_are_equivalent_compare_equal():
    assert ExchangeCode("nyse") == ExchangeCode("NYSE")


def test_different_exchange_codes_are_not_equal():
    assert ExchangeCode("NYSE") != ExchangeCode("NASDAQ")


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_exchange_codes_have_equal_hash():
    assert hash(ExchangeCode("NYSE")) == hash(ExchangeCode("NYSE"))


def test_exchange_code_is_usable_as_dictionary_key():
    index = {ExchangeCode("NYSE"): 100.0}

    assert index[ExchangeCode("nyse")] == 100.0


def test_exchange_code_is_usable_in_a_set():
    exchange_codes = {ExchangeCode("NYSE"), ExchangeCode("nyse"), ExchangeCode("NASDAQ")}

    assert len(exchange_codes) == 2


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_exchange_code_orders_lexically():
    assert ExchangeCode("NASDAQ") < ExchangeCode("NYSE")


def test_exchange_code_ordering_is_consistent_with_equality():
    a = ExchangeCode("NYSE")
    b = ExchangeCode("NYSE")

    assert not (a < b)
    assert not (a > b)


def test_sorted_exchange_codes_produce_lexical_order():
    exchange_codes = [ExchangeCode("NASDAQ"), ExchangeCode("NYSE"), ExchangeCode("LSE")]

    assert sorted(exchange_codes) == [
        ExchangeCode("LSE"),
        ExchangeCode("NASDAQ"),
        ExchangeCode("NYSE"),
    ]


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_the_canonical_value():
    assert str(ExchangeCode("NYSE")) == "NYSE"


def test_repr_contains_class_name_and_value():
    assert repr(ExchangeCode("NYSE")) == "ExchangeCode(value='NYSE')"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_minimum_length_exchange_code():
    exchange_code = ExchangeCode("NY")

    assert exchange_code.value == "NY"


def test_maximum_length_exchange_code():
    value = "A" * 16
    exchange_code = ExchangeCode(value)

    assert exchange_code.value == value


def test_underscore_is_accepted():
    exchange_code = ExchangeCode("NSE_FO")

    assert exchange_code.value == "NSE_FO"


def test_numeric_characters_are_accepted():
    exchange_code = ExchangeCode("B3")

    assert exchange_code.value == "B3"


def test_exchange_code_is_immutable():
    exchange_code = ExchangeCode("NYSE")

    with pytest.raises(AttributeError):
        exchange_code.value = "NASDAQ"
