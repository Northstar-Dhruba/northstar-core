"""Reference contract test suite for the QuotedMarketState value object.

This suite defines the Northstar Quote-specific Value Object contract for
QuotedMarketState.
"""

from decimal import Decimal

import pytest

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency, PointInTime, Price
from northstar_core.market_data.value_objects import (
    InvalidQuotedMarketStateError,
    QuotedMarketState,
)

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_quoted_market_state_from_single_price_value():
    state = QuotedMarketState((Price("100.00", Currency("USD")),))

    assert state.quotation_values == (Price("100", Currency("USD")),)


def test_creates_valid_quoted_market_state_from_multiple_price_values():
    state = QuotedMarketState(
        (
            Price("100", Currency("USD")),
            Price("101", Currency("USD")),
        )
    )

    assert state.quotation_values == (
        Price("100", Currency("USD")),
        Price("101", Currency("USD")),
    )


def test_preserves_tuple_composition():
    values = (
        Price("100", Currency("USD")),
        Price("100", Currency("EUR")),
    )

    state = QuotedMarketState(values)

    assert state.quotation_values == values


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none():
    with pytest.raises(InvalidQuotedMarketStateError, match="cannot be None"):
        QuotedMarketState(None)


def test_rejects_empty_tuple():
    with pytest.raises(InvalidQuotedMarketStateError, match="requires at least one"):
        QuotedMarketState(())


def test_rejects_tuple_containing_none():
    with pytest.raises(InvalidQuotedMarketStateError, match="cannot contain None"):
        QuotedMarketState((Price("100", Currency("USD")), None))


def test_rejects_non_price_values():
    with pytest.raises(InvalidQuotedMarketStateError, match="must compose Price values"):
        QuotedMarketState(("100 USD",))


def test_rejects_incorrect_collection_type_list():
    with pytest.raises(InvalidQuotedMarketStateError, match="must be a tuple"):
        QuotedMarketState([Price("100", Currency("USD"))])


def test_rejects_incorrect_collection_type_set():
    with pytest.raises(InvalidQuotedMarketStateError, match="must be a tuple"):
        QuotedMarketState({Price("100", Currency("USD"))})


def test_rejects_ambiguous_quotation_value_meaning_with_mixed_non_price_entries():
    with pytest.raises(InvalidQuotedMarketStateError, match="must compose Price values"):
        QuotedMarketState((Price("100", Currency("USD")), Decimal("1")))


def test_invalid_quoted_market_state_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        QuotedMarketState(None)


def test_invalid_quoted_market_state_error_is_a_value_error():
    with pytest.raises(ValueError):
        QuotedMarketState(None)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_tuple_composition_is_preserved_after_construction():
    values = (
        Price("100", Currency("USD")),
        Price("99", Currency("USD")),
    )

    state = QuotedMarketState(values)

    assert isinstance(state.quotation_values, tuple)
    assert state.quotation_values == values


def test_price_normalization_remains_authoritative_inside_quoted_market_state():
    state = QuotedMarketState((Price("100.000", Currency("USD")),))

    assert state.quotation_values[0].amount == Decimal("100")


def test_quoted_market_state_does_not_redefine_price_normalization_equivalence():
    left = QuotedMarketState((Price("100.00", Currency("USD")),))
    right = QuotedMarketState((Price("100", Currency("USD")),))

    assert left == right


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_quoted_market_state_values_compare_equal():
    assert QuotedMarketState((Price("100", Currency("USD")),)) == QuotedMarketState(
        (Price("100.00", Currency("USD")),)
    )


def test_equal_values_require_same_tuple_composition_order():
    left = QuotedMarketState((Price("100", Currency("USD")), Price("101", Currency("USD"))))
    right = QuotedMarketState((Price("101", Currency("USD")), Price("100", Currency("USD"))))

    assert left != right


def test_different_quotation_value_meaning_is_not_equal():
    assert QuotedMarketState((Price("100", Currency("USD")),)) != QuotedMarketState(
        (Price("101", Currency("USD")),)
    )


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_quoted_market_state_values_have_equal_hashes():
    assert hash(QuotedMarketState((Price("100", Currency("USD")),))) == hash(
        QuotedMarketState((Price("100.00", Currency("USD")),))
    )


def test_quoted_market_state_is_usable_as_dictionary_key():
    index = {QuotedMarketState((Price("100", Currency("USD")),)): "quoted"}

    assert index[QuotedMarketState((Price("100.00", Currency("USD")),))] == "quoted"


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_deterministic_comma_separated_representation_in_tuple_order():
    state = QuotedMarketState((Price("100", Currency("USD")), Price("101", Currency("USD"))))

    assert str(state) == "100 USD, 101 USD"


def test_repr_contains_class_name_and_composed_quotation_values():
    representation = repr(QuotedMarketState((Price("100", Currency("USD")),)))

    assert "QuotedMarketState" in representation
    assert "quotation_values" in representation
    assert "Price(" in representation


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_single_price_tuple_is_supported():
    state = QuotedMarketState((Price("100", Currency("USD")),))

    assert len(state.quotation_values) == 1


def test_multiple_price_tuple_is_supported():
    state = QuotedMarketState(
        (
            Price("100", Currency("USD")),
            Price("100", Currency("EUR")),
            Price("0", Currency("USD")),
        )
    )

    assert len(state.quotation_values) == 3


def test_tuple_order_is_preserved():
    first = Price("100", Currency("USD"))
    second = Price("101", Currency("USD"))
    state = QuotedMarketState((first, second))

    assert state.quotation_values[0] == first
    assert state.quotation_values[1] == second


def test_quoted_market_state_is_immutable():
    state = QuotedMarketState((Price("100", Currency("USD")),))

    with pytest.raises(AttributeError):
        state.quotation_values = (Price("101", Currency("USD")),)


def test_quoted_market_state_does_not_support_ordering():
    left = QuotedMarketState((Price("100", Currency("USD")),))
    right = QuotedMarketState((Price("101", Currency("USD")),))

    with pytest.raises(TypeError):
        _ = left < right


def test_quoted_market_state_remains_quote_specific_and_identity_free_shape():
    state = QuotedMarketState((Price("100", Currency("USD")),))

    assert hasattr(state, "quotation_values")
    assert not hasattr(state, "listing")
    assert not hasattr(state, "point_in_time")
    assert not isinstance(state, PointInTime)
