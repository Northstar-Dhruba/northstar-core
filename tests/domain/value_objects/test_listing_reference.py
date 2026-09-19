"""Reference contract test suite for the ListingReference value object.

This suite defines the Northstar Reference Identity Association Value Object
contract for ListingReference.
"""

import pytest

from northstar_core.domain.value_objects import (
    InvalidListingReferenceError,
    ListingReference,
)
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency, ExchangeCode, Symbol

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_listing_reference_from_symbol_and_exchange_code():
    symbol = Symbol("AAPL")
    exchange_code = ExchangeCode("NASDAQ")
    reference = ListingReference(symbol, exchange_code)

    assert reference.symbol is symbol
    assert reference.exchange_code is exchange_code


def test_preserves_canonical_symbol_and_exchange_code_composition():
    reference = ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))

    assert reference.symbol == Symbol("AAPL")
    assert reference.exchange_code == ExchangeCode("NASDAQ")


def test_constructs_deterministically_from_equivalent_identity_values():
    left = ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))
    right = ListingReference(Symbol(" aapl "), ExchangeCode(" nasdaq "))

    assert left == right


def test_supports_keyword_construction():
    reference = ListingReference(symbol=Symbol("MSFT"), exchange_code=ExchangeCode("NASDAQ"))

    assert reference.symbol == Symbol("MSFT")
    assert reference.exchange_code == ExchangeCode("NASDAQ")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none_symbol():
    with pytest.raises(InvalidListingReferenceError, match="symbol cannot be None"):
        ListingReference(None, ExchangeCode("NASDAQ"))


def test_rejects_none_exchange_code():
    with pytest.raises(InvalidListingReferenceError, match="exchange code cannot be None"):
        ListingReference(Symbol("AAPL"), None)


def test_rejects_invalid_symbol_type():
    with pytest.raises(InvalidListingReferenceError, match="must be a Symbol"):
        ListingReference("AAPL", ExchangeCode("NASDAQ"))


def test_rejects_invalid_exchange_code_type():
    with pytest.raises(InvalidListingReferenceError, match="must be an ExchangeCode"):
        ListingReference(Symbol("AAPL"), "NASDAQ")


def test_rejects_exchange_code_supplied_as_symbol():
    with pytest.raises(InvalidListingReferenceError, match="must be an ExchangeCode"):
        ListingReference(Symbol("AAPL"), Symbol("NASDAQ"))


def test_invalid_listing_reference_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        ListingReference(None, ExchangeCode("NASDAQ"))


def test_invalid_listing_reference_error_is_a_value_error():
    with pytest.raises(ValueError):
        ListingReference(None, ExchangeCode("NASDAQ"))


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def test_listing_reference_composes_exactly_one_symbol_and_one_exchange_code():
    symbol = Symbol("AAPL")
    exchange_code = ExchangeCode("NASDAQ")
    reference = ListingReference(symbol, exchange_code)

    assert isinstance(reference.symbol, Symbol)
    assert isinstance(reference.exchange_code, ExchangeCode)
    assert reference.symbol is symbol
    assert reference.exchange_code is exchange_code


def test_symbol_and_exchange_code_remain_authoritative_owners_of_identity_meaning():
    reference = ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))

    assert reference.symbol.value == "AAPL"
    assert reference.exchange_code.value == "NASDAQ"
    assert not hasattr(reference, "listing")


def test_listing_reference_does_not_compose_currency():
    reference = ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))

    assert not hasattr(reference, "currency")
    assert Currency not in {type(value) for value in (reference.symbol, reference.exchange_code)}


def test_listing_reference_does_not_compose_mutable_listing_state():
    reference = ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))

    assert not hasattr(reference, "listing_status")
    assert not hasattr(reference, "tradability")
    assert not hasattr(reference, "instrument")
    assert not hasattr(reference, "exchange")
    assert not hasattr(reference, "description")
    assert not hasattr(reference, "name")
    assert not hasattr(reference, "asset_class")


def test_listing_reference_does_not_compose_observation_or_provider_concepts():
    reference = ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))

    assert not hasattr(reference, "timeframe")
    assert not hasattr(reference, "point_in_time")
    assert not hasattr(reference, "provider")
    assert not hasattr(reference, "provider_symbol")
    assert not hasattr(reference, "source")
    assert not hasattr(reference, "is_historical")


def test_listing_reference_exposes_exactly_the_approved_identity_fields():
    reference = ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))

    assert ListingReference.__slots__ == ("symbol", "exchange_code")
    assert not hasattr(reference, "__dict__")


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_listing_reference_delegates_identity_normalization():
    reference = ListingReference(Symbol("  aapl  "), ExchangeCode("  nasdaq  "))

    assert reference.symbol.value == "AAPL"
    assert reference.exchange_code.value == "NASDAQ"


def test_listing_reference_does_not_redefine_identity_normalization():
    left = ListingReference(Symbol("  aapl  "), ExchangeCode("  nasdaq  "))
    right = ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))

    assert left == right
    assert left.symbol == right.symbol
    assert left.exchange_code == right.exchange_code


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_listing_references_compare_equal():
    assert ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ")) == ListingReference(
        Symbol("AAPL"), ExchangeCode("NASDAQ")
    )


def test_different_symbols_do_not_compare_equal():
    assert ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ")) != ListingReference(
        Symbol("MSFT"), ExchangeCode("NASDAQ")
    )


def test_different_exchange_codes_do_not_compare_equal():
    assert ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ")) != ListingReference(
        Symbol("AAPL"), ExchangeCode("NYSE")
    )


def test_listing_reference_equality_is_based_on_contained_identity_values():
    left = ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))
    right = ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))

    assert left == right
    assert left is not right


def test_listing_reference_does_not_compare_equal_to_unrelated_types():
    assert ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ")) != "AAPL@NASDAQ"


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_listing_references_have_equal_hashes():
    assert hash(ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))) == hash(
        ListingReference(Symbol(" aapl "), ExchangeCode(" nasdaq "))
    )


def test_listing_reference_is_usable_as_dictionary_key():
    index = {ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ")): "listing"}

    assert index[ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))] == "listing"


def test_listing_reference_is_usable_in_sets():
    references = {
        ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ")),
        ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ")),
        ListingReference(Symbol("MSFT"), ExchangeCode("NASDAQ")),
    }

    assert len(references) == 2


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_uses_canonical_symbol_at_exchange_representation():
    reference = ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))

    assert str(reference) == "AAPL@NASDAQ"


def test_repr_contains_listing_reference_symbol_and_exchange_code():
    representation = repr(ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ")))

    assert "ListingReference" in representation
    assert "Symbol" in representation
    assert "ExchangeCode" in representation
    assert "AAPL" in representation
    assert "NASDAQ" in representation


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_listing_reference_is_immutable():
    reference = ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))

    with pytest.raises(AttributeError):
        reference.symbol = Symbol("MSFT")


def test_listing_reference_exchange_code_is_immutable():
    reference = ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))

    with pytest.raises(AttributeError):
        reference.exchange_code = ExchangeCode("NYSE")


def test_listing_reference_does_not_support_ordering():
    left = ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))
    right = ListingReference(Symbol("MSFT"), ExchangeCode("NASDAQ"))

    with pytest.raises(TypeError):
        _ = left < right


def test_identity_association_is_preserved():
    symbol = Symbol("AAPL")
    exchange_code = ExchangeCode("NASDAQ")
    reference = ListingReference(symbol, exchange_code)

    assert reference.symbol is symbol
    assert reference.exchange_code is exchange_code


def test_listing_reference_does_not_introduce_business_interpretation():
    reference = ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))

    assert not hasattr(reference, "analysis")
    assert not hasattr(reference, "recommendation")
    assert not hasattr(reference, "strategy")
    assert not hasattr(reference, "observation")
    assert not hasattr(reference, "price")
    assert not hasattr(reference, "quantity")
    assert not hasattr(reference, "lifecycle")
    assert not hasattr(reference, "workflow")
