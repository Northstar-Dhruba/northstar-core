"""Reference contract test suite for the OrderBookState value object.

This suite defines the Northstar Market-Depth Observation Value Object
contract for OrderBookState.
"""

from decimal import Decimal

import pytest

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency, PointInTime, Price
from northstar_core.market_data.value_objects import (
    InvalidOrderBookStateError,
    OrderBookState,
)

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_order_book_state_from_single_price_value():
    state = OrderBookState((Price("100.00", Currency("USD")),))

    assert state.quotation_values == (Price("100", Currency("USD")),)


def test_creates_valid_order_book_state_from_multiple_price_values():
    state = OrderBookState(
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

    state = OrderBookState(values)

    assert state.quotation_values == values


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none():
    with pytest.raises(InvalidOrderBookStateError, match="cannot be None"):
        OrderBookState(None)


def test_rejects_empty_tuple():
    with pytest.raises(InvalidOrderBookStateError, match="requires at least one"):
        OrderBookState(())


def test_rejects_tuple_containing_none():
    with pytest.raises(InvalidOrderBookStateError, match="cannot contain None"):
        OrderBookState((Price("100", Currency("USD")), None))


def test_rejects_non_price_values():
    with pytest.raises(InvalidOrderBookStateError, match="must compose Price values"):
        OrderBookState(("100 USD",))


def test_rejects_incorrect_collection_type_list():
    with pytest.raises(InvalidOrderBookStateError, match="must be a tuple"):
        OrderBookState([Price("100", Currency("USD"))])


def test_rejects_incorrect_collection_type_set():
    with pytest.raises(InvalidOrderBookStateError, match="must be a tuple"):
        OrderBookState({Price("100", Currency("USD"))})


def test_rejects_ambiguous_market_depth_quotation_value_meaning_with_mixed_non_price_entries():
    with pytest.raises(InvalidOrderBookStateError, match="must compose Price values"):
        OrderBookState((Price("100", Currency("USD")), Decimal("1")))


def test_invalid_order_book_state_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        OrderBookState(None)


def test_invalid_order_book_state_error_is_a_value_error():
    with pytest.raises(ValueError):
        OrderBookState(None)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_tuple_composition_is_preserved_after_construction():
    values = (
        Price("100", Currency("USD")),
        Price("99", Currency("USD")),
    )

    state = OrderBookState(values)

    assert isinstance(state.quotation_values, tuple)
    assert state.quotation_values == values


def test_price_normalization_remains_authoritative_inside_order_book_state():
    state = OrderBookState((Price("100.000", Currency("USD")),))

    assert state.quotation_values[0].amount == Decimal("100")


def test_order_book_state_does_not_redefine_price_normalization_equivalence():
    left = OrderBookState((Price("100.00", Currency("USD")),))
    right = OrderBookState((Price("100", Currency("USD")),))

    assert left == right


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_order_book_state_values_compare_equal():
    assert OrderBookState((Price("100", Currency("USD")),)) == OrderBookState(
        (Price("100.00", Currency("USD")),)
    )


def test_equal_values_require_same_tuple_composition_order():
    left = OrderBookState((Price("100", Currency("USD")), Price("101", Currency("USD"))))
    right = OrderBookState((Price("101", Currency("USD")), Price("100", Currency("USD"))))

    assert left != right


def test_different_market_depth_quotation_value_meaning_is_not_equal():
    assert OrderBookState((Price("100", Currency("USD")),)) != OrderBookState(
        (Price("101", Currency("USD")),)
    )


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_order_book_state_values_have_equal_hashes():
    assert hash(OrderBookState((Price("100", Currency("USD")),))) == hash(
        OrderBookState((Price("100.00", Currency("USD")),))
    )


def test_order_book_state_is_usable_as_dictionary_key():
    index = {OrderBookState((Price("100", Currency("USD")),)): "market-depth-meaning"}

    assert index[OrderBookState((Price("100.00", Currency("USD")),))] == ("market-depth-meaning")


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_deterministic_canonical_business_representation():
    state = OrderBookState((Price("100", Currency("USD")), Price("101", Currency("USD"))))
    repeated_state = OrderBookState(
        (Price("100.00", Currency("USD")), Price("101.00", Currency("USD")))
    )

    assert str(state) == str(repeated_state)
    assert str(state).index("100 USD") < str(state).index("101 USD")


def test_repr_contains_class_name_and_composed_quotation_values():
    representation = repr(OrderBookState((Price("100", Currency("USD")),)))

    assert "OrderBookState" in representation
    assert "quotation_values" in representation
    assert "Price(" in representation


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_single_price_tuple_is_supported():
    state = OrderBookState((Price("100", Currency("USD")),))

    assert len(state.quotation_values) == 1


def test_multiple_price_tuple_is_supported():
    state = OrderBookState(
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
    state = OrderBookState((first, second))

    assert state.quotation_values[0] == first
    assert state.quotation_values[1] == second


def test_order_book_state_is_immutable():
    state = OrderBookState((Price("100", Currency("USD")),))

    with pytest.raises(AttributeError):
        state.quotation_values = (Price("101", Currency("USD")),)


def test_order_book_state_does_not_support_ordering():
    left = OrderBookState((Price("100", Currency("USD")),))
    right = OrderBookState((Price("101", Currency("USD")),))

    with pytest.raises(TypeError):
        _ = left < right


def test_order_book_state_remains_order_book_specific_and_identity_free_shape():
    state = OrderBookState((Price("100", Currency("USD")),))

    assert hasattr(state, "quotation_values")
    assert not hasattr(state, "listing")
    assert not hasattr(state, "point_in_time")
    assert not hasattr(state, "currency")
    assert not isinstance(state, PointInTime)
