"""Reference contract test suite for the TradeIdentity value object.

This suite defines the Northstar Reference Aggregate Identity Value Object
contract for TradeIdentity.
"""

import pytest

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.trades.value_objects import InvalidTradeIdentityError, TradeIdentity

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_trade_identity_from_opaque_identity():
    trade_identity = TradeIdentity("trade-opaque-001")

    assert trade_identity.identity == "trade-opaque-001"


def test_normalizes_surrounding_whitespace_from_opaque_identity():
    trade_identity = TradeIdentity("  trade-opaque-001  ")

    assert trade_identity.identity == "trade-opaque-001"


def test_preserves_canonical_opaque_trade_identity():
    trade_identity = TradeIdentity("opaque-trade-reference")

    assert str(trade_identity) == "opaque-trade-reference"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none():
    with pytest.raises(InvalidTradeIdentityError, match="cannot be None"):
        TradeIdentity(None)


def test_rejects_empty_value():
    with pytest.raises(InvalidTradeIdentityError, match="cannot be empty"):
        TradeIdentity("")


def test_rejects_whitespace_only_value():
    with pytest.raises(InvalidTradeIdentityError, match="cannot be empty"):
        TradeIdentity("   ")


def test_rejects_incorrect_type():
    with pytest.raises(InvalidTradeIdentityError, match="must be a string"):
        TradeIdentity(1)


def test_invalid_trade_identity_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        TradeIdentity(None)


def test_invalid_trade_identity_error_is_a_value_error():
    with pytest.raises(ValueError):
        TradeIdentity(None)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_surrounding_whitespace_is_removed():
    trade_identity = TradeIdentity("\t trade-opaque-001 \n")

    assert trade_identity.identity == "trade-opaque-001"


def test_normalization_preserves_deterministic_comparison():
    left = TradeIdentity("  trade-opaque-001")
    right = TradeIdentity("trade-opaque-001  ")

    assert left == right


def test_normalization_does_not_derive_business_meaning():
    trade_identity = TradeIdentity("Order-AAPL-Participant-100-USD")

    assert trade_identity.identity == "Order-AAPL-Participant-100-USD"
    assert str(trade_identity) == "Order-AAPL-Participant-100-USD"


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_trade_identity_values_compare_equal():
    assert TradeIdentity("trade-opaque-001") == TradeIdentity("trade-opaque-001")


def test_different_opaque_trade_identities_are_not_equal():
    assert TradeIdentity("trade-opaque-001") != TradeIdentity("trade-opaque-002")


def test_identity_equality_is_independent_of_business_attributes():
    left = TradeIdentity("opaque-left")
    right = TradeIdentity("opaque-right")

    assert left != right


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_trade_identity_values_have_equal_hashes():
    assert hash(TradeIdentity("trade-opaque-001")) == hash(TradeIdentity(" trade-opaque-001 "))


def test_trade_identity_is_usable_as_dictionary_key():
    index = {TradeIdentity("trade-opaque-001"): "trade"}

    assert index[TradeIdentity("  trade-opaque-001  ")] == "trade"


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_deterministic_canonical_business_representation():
    assert str(TradeIdentity("  trade-opaque-001  ")) == "trade-opaque-001"


def test_repr_contains_trade_identity_and_opaque_identity():
    representation = repr(TradeIdentity("trade-opaque-001"))

    assert "TradeIdentity" in representation
    assert "trade-opaque-001" in representation
    assert "identity" in representation


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_trade_identity_is_immutable():
    trade_identity = TradeIdentity("trade-opaque-001")

    with pytest.raises(AttributeError):
        trade_identity.identity = "trade-opaque-002"


def test_trade_identity_does_not_support_ordering():
    left = TradeIdentity("trade-opaque-001")
    right = TradeIdentity("trade-opaque-002")

    with pytest.raises(TypeError):
        _ = left < right


def test_opaque_trade_identity_remains_uninterpreted():
    trade_identity = TradeIdentity("not-a-uuid-or-database-key")

    assert trade_identity.identity == "not-a-uuid-or-database-key"


def test_trade_identity_does_not_expose_business_context():
    trade_identity = TradeIdentity("trade-opaque-001")

    assert not hasattr(trade_identity, "listing")
    assert not hasattr(trade_identity, "participant")
    assert not hasattr(trade_identity, "participant_reference")
    assert not hasattr(trade_identity, "quantity")
    assert not hasattr(trade_identity, "price")
    assert not hasattr(trade_identity, "point_in_time")
    assert not hasattr(trade_identity, "order")
    assert not hasattr(trade_identity, "order_identity")
    assert not hasattr(trade_identity, "market_data")
    assert not hasattr(trade_identity, "portfolio")
    assert not hasattr(trade_identity, "settlement")
    assert not hasattr(trade_identity, "workflow")
