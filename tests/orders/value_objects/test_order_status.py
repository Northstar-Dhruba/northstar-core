"""Reference contract test suite for the OrderStatus value object.

This suite defines the Northstar Reference Lifecycle Value Object contract for
OrderStatus.
"""

import pytest

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency, Price
from northstar_core.market_data.value_objects import OrderBookState
from northstar_core.orders.value_objects import InvalidOrderStatusError, OrderStatus

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_order_status_from_lifecycle_meaning():
    status = OrderStatus("Submitted")

    assert status.lifecycle_meaning == "Submitted"


def test_normalizes_surrounding_whitespace_from_lifecycle_meaning():
    status = OrderStatus("  Submitted  ")

    assert status.lifecycle_meaning == "Submitted"


def test_preserves_canonical_lifecycle_meaning():
    status = OrderStatus("Accepted")

    assert str(status) == "Accepted"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none():
    with pytest.raises(InvalidOrderStatusError, match="cannot be None"):
        OrderStatus(None)


def test_rejects_empty_value():
    with pytest.raises(InvalidOrderStatusError, match="cannot be empty"):
        OrderStatus("")


def test_rejects_whitespace_only_value():
    with pytest.raises(InvalidOrderStatusError, match="cannot be empty"):
        OrderStatus("   ")


def test_rejects_incorrect_type():
    with pytest.raises(InvalidOrderStatusError, match="must be a string"):
        OrderStatus(1)


def test_invalid_order_status_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        OrderStatus(None)


def test_invalid_order_status_error_is_a_value_error():
    with pytest.raises(ValueError):
        OrderStatus(None)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_surrounding_whitespace_is_removed():
    status = OrderStatus("\t Submitted \n")

    assert status.lifecycle_meaning == "Submitted"


def test_normalization_preserves_deterministic_comparison():
    left = OrderStatus("  Submitted")
    right = OrderStatus("Submitted  ")

    assert left == right


def test_normalization_does_not_invent_lifecycle_vocabulary():
    status = OrderStatus("ApprovedByVenue")

    assert status.lifecycle_meaning == "ApprovedByVenue"


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_order_status_values_compare_equal():
    assert OrderStatus("Submitted") == OrderStatus("  Submitted  ")


def test_different_lifecycle_meaning_is_not_equal():
    assert OrderStatus("Submitted") != OrderStatus("Accepted")


def test_order_status_equality_is_independent_of_observation_state_types():
    status = OrderStatus("Submitted")
    observation_state = OrderBookState((Price("100", Currency("USD")),))

    assert status != observation_state


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_order_status_values_have_equal_hashes():
    assert hash(OrderStatus("Submitted")) == hash(OrderStatus(" Submitted "))


def test_order_status_is_usable_as_dictionary_key():
    index = {OrderStatus("Submitted"): "lifecycle"}

    assert index[OrderStatus("  Submitted  ")] == "lifecycle"


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_deterministic_canonical_business_representation():
    assert str(OrderStatus("  Submitted  ")) == str(OrderStatus("Submitted"))


def test_repr_contains_order_status_and_lifecycle_meaning():
    representation = repr(OrderStatus("Submitted"))

    assert "OrderStatus" in representation
    assert "Submitted" in representation
    assert "lifecycle_meaning" in representation


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_order_status_is_immutable():
    status = OrderStatus("Submitted")

    with pytest.raises(AttributeError):
        status.lifecycle_meaning = "Accepted"


def test_order_status_does_not_support_ordering():
    left = OrderStatus("Submitted")
    right = OrderStatus("Accepted")

    with pytest.raises(TypeError):
        _ = left < right


def test_order_status_is_identity_free():
    status = OrderStatus("Submitted")

    assert hasattr(status, "lifecycle_meaning")
    assert not hasattr(status, "value")
    assert not hasattr(status, "listing")
    assert not hasattr(status, "point_in_time")
    assert not hasattr(status, "participant")
    assert not hasattr(status, "quantity")
    assert not hasattr(status, "price")


def test_order_status_remains_lifecycle_specific():
    status = OrderStatus("Submitted")

    assert not isinstance(status, OrderBookState)
    assert not hasattr(status, "quotation_values")
    assert status.lifecycle_meaning == "Submitted"
