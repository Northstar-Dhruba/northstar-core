"""Reference contract test suite for the OrderIdentity value object.

This suite defines the Northstar Reference Aggregate Identity Value Object
contract for OrderIdentity.
"""

import pytest

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.orders.value_objects import InvalidOrderIdentityError, OrderIdentity

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_order_identity_from_opaque_identity():
    order_identity = OrderIdentity("order-opaque-001")

    assert order_identity.identity == "order-opaque-001"


def test_normalizes_surrounding_whitespace_from_opaque_identity():
    order_identity = OrderIdentity("  order-opaque-001  ")

    assert order_identity.identity == "order-opaque-001"


def test_preserves_canonical_opaque_identity():
    order_identity = OrderIdentity("opaque-order-reference")

    assert str(order_identity) == "opaque-order-reference"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none():
    with pytest.raises(InvalidOrderIdentityError, match="cannot be None"):
        OrderIdentity(None)


def test_rejects_empty_value():
    with pytest.raises(InvalidOrderIdentityError, match="cannot be empty"):
        OrderIdentity("")


def test_rejects_whitespace_only_value():
    with pytest.raises(InvalidOrderIdentityError, match="cannot be empty"):
        OrderIdentity("   ")


def test_rejects_incorrect_type():
    with pytest.raises(InvalidOrderIdentityError, match="must be a string"):
        OrderIdentity(1)


def test_invalid_order_identity_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        OrderIdentity(None)


def test_invalid_order_identity_error_is_a_value_error():
    with pytest.raises(ValueError):
        OrderIdentity(None)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_surrounding_whitespace_is_removed():
    order_identity = OrderIdentity("\t order-opaque-001 \n")

    assert order_identity.identity == "order-opaque-001"


def test_normalization_preserves_deterministic_comparison():
    left = OrderIdentity("  order-opaque-001")
    right = OrderIdentity("order-opaque-001  ")

    assert left == right


def test_normalization_does_not_derive_business_meaning():
    order_identity = OrderIdentity("Participant-AAPL-100-Submitted")

    assert order_identity.identity == "Participant-AAPL-100-Submitted"
    assert str(order_identity) == "Participant-AAPL-100-Submitted"


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_order_identity_values_compare_equal():
    assert OrderIdentity("order-opaque-001") == OrderIdentity("order-opaque-001")


def test_different_opaque_identities_are_not_equal():
    assert OrderIdentity("order-opaque-001") != OrderIdentity("order-opaque-002")


def test_identity_equality_is_independent_of_business_attributes():
    left = OrderIdentity("opaque-left")
    right = OrderIdentity("opaque-right")

    assert left != right


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_order_identity_values_have_equal_hashes():
    assert hash(OrderIdentity("order-opaque-001")) == hash(OrderIdentity(" order-opaque-001 "))


def test_order_identity_is_usable_as_dictionary_key():
    index = {OrderIdentity("order-opaque-001"): "order"}

    assert index[OrderIdentity("  order-opaque-001  ")] == "order"


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_deterministic_canonical_business_representation():
    assert str(OrderIdentity("  order-opaque-001  ")) == "order-opaque-001"


def test_repr_contains_order_identity_and_opaque_identity():
    representation = repr(OrderIdentity("order-opaque-001"))

    assert "OrderIdentity" in representation
    assert "order-opaque-001" in representation
    assert "identity" in representation


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_order_identity_is_immutable():
    order_identity = OrderIdentity("order-opaque-001")

    with pytest.raises(AttributeError):
        order_identity.identity = "order-opaque-002"


def test_order_identity_does_not_support_ordering():
    left = OrderIdentity("order-opaque-001")
    right = OrderIdentity("order-opaque-002")

    with pytest.raises(TypeError):
        _ = left < right


def test_opaque_identity_remains_uninterpreted():
    order_identity = OrderIdentity("not-a-uuid-or-database-key")

    assert order_identity.identity == "not-a-uuid-or-database-key"


def test_order_identity_does_not_expose_business_context():
    order_identity = OrderIdentity("order-opaque-001")

    assert not hasattr(order_identity, "listing")
    assert not hasattr(order_identity, "participant")
    assert not hasattr(order_identity, "participant_reference")
    assert not hasattr(order_identity, "quantity")
    assert not hasattr(order_identity, "price")
    assert not hasattr(order_identity, "point_in_time")
    assert not hasattr(order_identity, "order_status")
    assert not hasattr(order_identity, "market_data")
