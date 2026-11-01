"""Reference test suite for the Symbol value object.

This suite defines the Northstar Value Object Testing Standard v1.0.
Future value object tests should follow this structure.
"""

import pytest

from northstar_core.foundation.exceptions.validation import (
    InvalidSymbolError,
    ValidationError,
)
from northstar_core.foundation.value_objects import Symbol

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_symbol():
    symbol = Symbol("AAPL")

    assert symbol.value == "AAPL"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none():
    with pytest.raises(InvalidSymbolError, match="Symbol cannot be None"):
        Symbol(None)


def test_rejects_empty_string():
    with pytest.raises(InvalidSymbolError, match="Symbol cannot be empty"):
        Symbol("")


def test_rejects_whitespace_only():
    with pytest.raises(InvalidSymbolError, match="Symbol cannot be empty"):
        Symbol("   ")


def test_rejects_embedded_whitespace():
    with pytest.raises(InvalidSymbolError, match="Symbol contains whitespace"):
        Symbol("BTC USDT")


def test_rejects_invalid_characters():
    with pytest.raises(InvalidSymbolError, match="Symbol contains invalid characters"):
        Symbol("AAPL!")


def test_rejects_symbol_exceeding_maximum_length():
    with pytest.raises(InvalidSymbolError, match="Symbol exceeds maximum length"):
        Symbol("A" * 33)


def test_invalid_symbol_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        Symbol("")


def test_invalid_symbol_error_is_a_value_error():
    with pytest.raises(ValueError):
        Symbol("")


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_trims_leading_whitespace():
    symbol = Symbol("  AAPL")

    assert symbol.value == "AAPL"


def test_trims_trailing_whitespace():
    symbol = Symbol("AAPL  ")

    assert symbol.value == "AAPL"


def test_trims_leading_and_trailing_whitespace():
    symbol = Symbol("  AAPL  ")

    assert symbol.value == "AAPL"


def test_normalizes_lowercase_to_uppercase():
    symbol = Symbol("aapl")

    assert symbol.value == "AAPL"


def test_normalizes_mixed_case_to_uppercase():
    symbol = Symbol("AaPl")

    assert symbol.value == "AAPL"


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_symbols_compare_equal():
    assert Symbol("AAPL") == Symbol("AAPL")


def test_normalized_inputs_that_are_equivalent_compare_equal():
    assert Symbol("aapl") == Symbol("AAPL")


def test_different_symbols_are_not_equal():
    assert Symbol("AAPL") != Symbol("MSFT")


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_symbols_have_equal_hash():
    assert hash(Symbol("AAPL")) == hash(Symbol("AAPL"))


def test_symbol_is_usable_as_dictionary_key():
    index = {Symbol("AAPL"): 100.0}

    assert index[Symbol("aapl")] == 100.0


def test_symbol_is_usable_in_a_set():
    symbols = {Symbol("AAPL"), Symbol("aapl"), Symbol("MSFT")}

    assert len(symbols) == 2


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_symbol_orders_lexically():
    assert Symbol("AAPL") < Symbol("MSFT")


def test_symbol_ordering_is_consistent_with_equality():
    a = Symbol("AAPL")
    b = Symbol("AAPL")

    assert not (a < b)
    assert not (a > b)


def test_sorted_symbols_produce_lexical_order():
    symbols = [Symbol("MSFT"), Symbol("AAPL"), Symbol("GOOG")]

    assert sorted(symbols) == [Symbol("AAPL"), Symbol("GOOG"), Symbol("MSFT")]


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_the_canonical_value():
    assert str(Symbol("AAPL")) == "AAPL"


def test_repr_contains_class_name_and_value():
    assert repr(Symbol("AAPL")) == "Symbol(value='AAPL')"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_minimum_length_symbol():
    symbol = Symbol("A")

    assert symbol.value == "A"


def test_maximum_length_symbol():
    value = "A" * 32
    symbol = Symbol(value)

    assert symbol.value == value


def test_dot_notation_is_accepted():
    symbol = Symbol("BRK.B")

    assert symbol.value == "BRK.B"


def test_underscore_is_accepted():
    symbol = Symbol("NIFTY_50")

    assert symbol.value == "NIFTY_50"


def test_hyphen_is_accepted():
    symbol = Symbol("BTC-USDT")

    assert symbol.value == "BTC-USDT"


def test_numeric_characters_are_accepted():
    symbol = Symbol("NIFTY50")

    assert symbol.value == "NIFTY50"


def test_complex_derivative_symbol_is_accepted():
    symbol = Symbol("BANKNIFTY26AUG25000CE")

    assert symbol.value == "BANKNIFTY26AUG25000CE"


def test_symbol_is_immutable():
    symbol = Symbol("AAPL")

    with pytest.raises(AttributeError):
        symbol.value = "MSFT"


# ---------------------------------------------------------------------------
# Ampersand (ADR-019)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["M&M", "M&MFIN", "J&KBANK", "M&M.NS"])
def test_ampersand_is_accepted(value):
    symbol = Symbol(value)

    assert symbol.value == value


def test_ampersand_symbol_is_normalized_to_uppercase():
    assert Symbol("m&m").value == "M&M"
    assert Symbol("j&kBank").value == "J&KBANK"


def test_ampersand_symbol_is_trimmed():
    assert Symbol("  M&M  ").value == "M&M"


def test_ampersand_within_maximum_length_symbol_is_accepted():
    value = "A" * 15 + "&" + "B" * 16
    symbol = Symbol(value)

    assert len(value) == 32
    assert symbol.value == value


def test_ampersand_symbol_exceeding_maximum_length_is_rejected():
    with pytest.raises(InvalidSymbolError, match="Symbol exceeds maximum length"):
        Symbol("A" * 16 + "&" + "B" * 16)


def test_ampersand_symbol_with_embedded_whitespace_is_rejected():
    with pytest.raises(InvalidSymbolError, match="Symbol contains whitespace"):
        Symbol("M & M")


@pytest.mark.parametrize("value", ["M!M", "M/M", "M#M", "M+M", "M@M", "M=M", "M%26M"])
def test_other_punctuation_remains_rejected(value):
    with pytest.raises(InvalidSymbolError, match="Symbol contains invalid characters"):
        Symbol(value)


@pytest.mark.parametrize("value", [42, b"M&M", ["M&M"]])
def test_non_string_input_remains_rejected(value):
    with pytest.raises(InvalidSymbolError, match="Symbol must be a string"):
        Symbol(value)


def test_ampersand_symbol_is_distinct_from_symbol_without_it():
    assert Symbol("M&M") != Symbol("MM")
    assert hash(Symbol("M&M")) == hash(Symbol("m&m"))
    assert len({Symbol("M&M"), Symbol("m&m"), Symbol("MM")}) == 2


def test_ampersand_symbol_orders_by_its_canonical_value():
    # "&" precedes digits and letters in the canonical value, as any string comparison does.
    assert sorted([Symbol("MM"), Symbol("M1"), Symbol("M&M")]) == [
        Symbol("M&M"),
        Symbol("M1"),
        Symbol("MM"),
    ]


def test_ampersand_symbol_representation_preserves_ampersand():
    assert str(Symbol("M&M")) == "M&M"
    assert repr(Symbol("M&M")) == "Symbol(value='M&M')"


@pytest.mark.parametrize(
    "value",
    ["AAPL", "BRK.B", "NIFTY_50", "BTC-USDT", "NIFTY50", "BANKNIFTY26AUG25000CE", "A" * 32],
)
def test_previously_valid_symbols_keep_their_canonical_value(value):
    assert Symbol(value).value == value
    assert Symbol(f" {value.lower()} ") == Symbol(value)
