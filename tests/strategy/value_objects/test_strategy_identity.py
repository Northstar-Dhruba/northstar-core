"""Reference contract test suite for the StrategyIdentity value object.

This suite defines the Northstar Reference Aggregate Identity Value Object
contract for StrategyIdentity.
"""

import pytest

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.strategy.value_objects import (
    InvalidStrategyIdentityError,
    StrategyIdentity,
)

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_strategy_identity_from_opaque_identity():
    strategy_identity = StrategyIdentity("strategy-opaque-001")

    assert strategy_identity.identity == "strategy-opaque-001"


def test_normalizes_surrounding_whitespace_from_opaque_identity():
    strategy_identity = StrategyIdentity("  strategy-opaque-001  ")

    assert strategy_identity.identity == "strategy-opaque-001"


def test_preserves_canonical_opaque_strategy_identity():
    strategy_identity = StrategyIdentity("opaque-strategy-reference")

    assert str(strategy_identity) == "opaque-strategy-reference"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none():
    with pytest.raises(InvalidStrategyIdentityError, match="cannot be None"):
        StrategyIdentity(None)


def test_rejects_empty_value():
    with pytest.raises(InvalidStrategyIdentityError, match="cannot be empty"):
        StrategyIdentity("")


def test_rejects_whitespace_only_value():
    with pytest.raises(InvalidStrategyIdentityError, match="cannot be empty"):
        StrategyIdentity("   ")


def test_rejects_incorrect_type():
    with pytest.raises(InvalidStrategyIdentityError, match="must be a string"):
        StrategyIdentity(1)


def test_invalid_strategy_identity_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        StrategyIdentity(None)


def test_invalid_strategy_identity_error_is_a_value_error():
    with pytest.raises(ValueError):
        StrategyIdentity(None)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_surrounding_whitespace_is_removed():
    strategy_identity = StrategyIdentity("\t strategy-opaque-001 \n")

    assert strategy_identity.identity == "strategy-opaque-001"


def test_normalization_preserves_deterministic_comparison():
    left = StrategyIdentity("  strategy-opaque-001")
    right = StrategyIdentity("strategy-opaque-001  ")

    assert left == right


def test_normalization_does_not_derive_strategy_policy_meaning():
    strategy_identity = StrategyIdentity("MarketData-Portfolio-Order-Policy")

    assert strategy_identity.identity == "MarketData-Portfolio-Order-Policy"
    assert str(strategy_identity) == "MarketData-Portfolio-Order-Policy"


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_strategy_identity_values_compare_equal():
    assert StrategyIdentity("strategy-opaque-001") == StrategyIdentity("strategy-opaque-001")


def test_different_opaque_strategy_identities_are_not_equal():
    assert StrategyIdentity("strategy-opaque-001") != StrategyIdentity("strategy-opaque-002")


def test_identity_equality_is_independent_of_strategy_policy():
    assert StrategyIdentity("opaque-left") != StrategyIdentity("opaque-right")


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_strategy_identity_values_have_equal_hashes():
    assert hash(StrategyIdentity("strategy-opaque-001")) == hash(
        StrategyIdentity(" strategy-opaque-001 ")
    )


def test_strategy_identity_is_usable_as_dictionary_key():
    index = {StrategyIdentity("strategy-opaque-001"): "strategy"}

    assert index[StrategyIdentity("  strategy-opaque-001  ")] == "strategy"


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_deterministic_canonical_business_representation():
    assert str(StrategyIdentity("  strategy-opaque-001  ")) == "strategy-opaque-001"


def test_repr_contains_strategy_identity_and_opaque_identity():
    representation = repr(StrategyIdentity("strategy-opaque-001"))

    assert "StrategyIdentity" in representation
    assert "strategy-opaque-001" in representation
    assert "identity" in representation


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_strategy_identity_is_immutable():
    strategy_identity = StrategyIdentity("strategy-opaque-001")

    with pytest.raises(AttributeError):
        strategy_identity.identity = "strategy-opaque-002"


def test_strategy_identity_does_not_support_ordering():
    with pytest.raises(TypeError):
        _ = StrategyIdentity("strategy-opaque-001") < StrategyIdentity("strategy-opaque-002")


def test_opaque_strategy_identity_remains_uninterpreted():
    strategy_identity = StrategyIdentity("not-a-uuid-or-database-key")

    assert strategy_identity.identity == "not-a-uuid-or-database-key"


def test_strategy_identity_does_not_expose_business_context():
    strategy_identity = StrategyIdentity("strategy-opaque-001")

    assert not hasattr(strategy_identity, "strategy_policy")
    assert not hasattr(strategy_identity, "participant")
    assert not hasattr(strategy_identity, "participant_reference")
    assert not hasattr(strategy_identity, "orders")
    assert not hasattr(strategy_identity, "trades")
    assert not hasattr(strategy_identity, "portfolio")
    assert not hasattr(strategy_identity, "market_data")
    assert not hasattr(strategy_identity, "risk")
    assert not hasattr(strategy_identity, "performance")
    assert not hasattr(strategy_identity, "workflow")
