"""Reference contract test suite for the TickState value object.

This suite defines the Northstar Reference High-Frequency Point Observation
Value Object contract for TickState.
"""

from decimal import Decimal

import pytest

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency, PointInTime, Price
from northstar_core.market_data.value_objects import InvalidTickStateError, TickState

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_tick_state_from_single_price_value():
    state = TickState((Price("100.00", Currency("USD")),))

    assert state.quotation_values == (Price("100", Currency("USD")),)


def test_creates_valid_tick_state_from_multiple_price_values():
    state = TickState(
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

    state = TickState(values)

    assert state.quotation_values == values


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none():
    with pytest.raises(InvalidTickStateError, match="cannot be None"):
        TickState(None)


def test_rejects_empty_tuple():
    with pytest.raises(InvalidTickStateError, match="requires at least one"):
        TickState(())


def test_rejects_tuple_containing_none():
    with pytest.raises(InvalidTickStateError, match="cannot contain None"):
        TickState((Price("100", Currency("USD")), None))


def test_rejects_non_price_values():
    with pytest.raises(InvalidTickStateError, match="must compose Price values"):
        TickState(("100 USD",))


def test_rejects_incorrect_collection_type_list():
    with pytest.raises(InvalidTickStateError, match="must be a tuple"):
        TickState([Price("100", Currency("USD"))])


def test_rejects_incorrect_collection_type_set():
    with pytest.raises(InvalidTickStateError, match="must be a tuple"):
        TickState({Price("100", Currency("USD"))})


def test_rejects_ambiguous_point_quotation_value_meaning_with_mixed_non_price_entries():
    with pytest.raises(InvalidTickStateError, match="must compose Price values"):
        TickState((Price("100", Currency("USD")), Decimal("1")))


def test_invalid_tick_state_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        TickState(None)


def test_invalid_tick_state_error_is_a_value_error():
    with pytest.raises(ValueError):
        TickState(None)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_tuple_composition_is_preserved_after_construction():
    values = (
        Price("100", Currency("USD")),
        Price("99", Currency("USD")),
    )

    state = TickState(values)

    assert isinstance(state.quotation_values, tuple)
    assert state.quotation_values == values


def test_price_normalization_remains_authoritative_inside_tick_state():
    state = TickState((Price("100.000", Currency("USD")),))

    assert state.quotation_values[0].amount == Decimal("100")


def test_tick_state_does_not_redefine_price_normalization_equivalence():
    left = TickState((Price("100.00", Currency("USD")),))
    right = TickState((Price("100", Currency("USD")),))

    assert left == right


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_tick_state_values_compare_equal():
    assert TickState((Price("100", Currency("USD")),)) == TickState(
        (Price("100.00", Currency("USD")),)
    )


def test_equal_values_require_same_tuple_composition_order():
    left = TickState((Price("100", Currency("USD")), Price("101", Currency("USD"))))
    right = TickState((Price("101", Currency("USD")), Price("100", Currency("USD"))))

    assert left != right


def test_different_point_quotation_value_meaning_is_not_equal():
    assert TickState((Price("100", Currency("USD")),)) != TickState(
        (Price("101", Currency("USD")),)
    )


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_tick_state_values_have_equal_hashes():
    assert hash(TickState((Price("100", Currency("USD")),))) == hash(
        TickState((Price("100.00", Currency("USD")),))
    )


def test_tick_state_is_usable_as_dictionary_key():
    index = {TickState((Price("100", Currency("USD")),)): "point-meaning"}

    assert index[TickState((Price("100.00", Currency("USD")),))] == "point-meaning"


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_deterministic_canonical_business_representation():
    state = TickState((Price("100", Currency("USD")), Price("101", Currency("USD"))))

    assert str(state) == "100 USD, 101 USD"


def test_repr_contains_class_name_and_composed_quotation_values():
    representation = repr(TickState((Price("100", Currency("USD")),)))

    assert "TickState" in representation
    assert "quotation_values" in representation
    assert "Price(" in representation


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_single_price_tuple_is_supported():
    state = TickState((Price("100", Currency("USD")),))

    assert len(state.quotation_values) == 1


def test_multiple_price_tuple_is_supported():
    state = TickState(
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
    state = TickState((first, second))

    assert state.quotation_values[0] == first
    assert state.quotation_values[1] == second


def test_tick_state_is_immutable():
    state = TickState((Price("100", Currency("USD")),))

    with pytest.raises(AttributeError):
        state.quotation_values = (Price("101", Currency("USD")),)


def test_tick_state_does_not_support_ordering():
    left = TickState((Price("100", Currency("USD")),))
    right = TickState((Price("101", Currency("USD")),))

    with pytest.raises(TypeError):
        _ = left < right


def test_tick_state_remains_tick_specific_and_identity_free_shape():
    state = TickState((Price("100", Currency("USD")),))

    assert hasattr(state, "quotation_values")
    assert not hasattr(state, "listing")
    assert not hasattr(state, "point_in_time")
    assert not isinstance(state, PointInTime)
