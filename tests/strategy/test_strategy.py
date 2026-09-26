"""Reference contract test suite for the Strategy aggregate root.

This suite defines the Northstar Reference Strategy Aggregate Contract.
"""

import pytest

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.strategy import InvalidStrategyError, Strategy, StrategyIdentity


def _build_identity(value: str = "strategy-opaque-001") -> StrategyIdentity:
    return StrategyIdentity(value)


def _build_strategy(value: str = "strategy-opaque-001") -> Strategy:
    return Strategy(_build_identity(value))


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_strategy_from_approved_aggregate_composition():
    strategy = _build_strategy()

    assert isinstance(strategy, Strategy)
    assert strategy.strategy_identity.identity == "strategy-opaque-001"


def test_strategy_composes_only_strategy_identity():
    strategy = _build_strategy()

    assert isinstance(strategy.strategy_identity, StrategyIdentity)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none_strategy_identity():
    with pytest.raises(InvalidStrategyError, match="identity cannot be None"):
        Strategy(None)


def test_rejects_invalid_strategy_identity_type():
    with pytest.raises(InvalidStrategyError, match="identity must be a StrategyIdentity"):
        Strategy("strategy-opaque-001")


def test_invalid_strategy_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        Strategy(None)


def test_invalid_strategy_error_is_a_value_error():
    with pytest.raises(ValueError):
        Strategy(None)


# ---------------------------------------------------------------------------
# Aggregate Composition
# ---------------------------------------------------------------------------


def test_strategy_does_not_compose_optional_or_external_contexts():
    strategy = _build_strategy()

    assert not hasattr(strategy, "participant_reference")
    assert not hasattr(strategy, "point_in_time")
    assert not hasattr(strategy, "market_data")
    assert not hasattr(strategy, "portfolio")
    assert not hasattr(strategy, "trade")
    assert not hasattr(strategy, "order")
    assert not hasattr(strategy, "execution")
    assert not hasattr(strategy, "risk")
    assert not hasattr(strategy, "performance")
    assert not hasattr(strategy, "workflow")


def test_strategy_identity_remains_authoritative_owner_of_identity_meaning():
    identity = _build_identity()
    strategy = Strategy(identity)

    assert strategy.strategy_identity is identity
    assert strategy.strategy_identity.identity == "strategy-opaque-001"


# ---------------------------------------------------------------------------
# Identity Semantics
# ---------------------------------------------------------------------------


def test_strategies_with_same_identity_compare_equal():
    left = _build_strategy("strategy-opaque-001")
    right = _build_strategy(" strategy-opaque-001 ")

    assert left == right


def test_strategies_with_different_identity_do_not_compare_equal():
    assert _build_strategy("strategy-opaque-001") != _build_strategy("strategy-opaque-002")


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_strategies_have_equal_hashes():
    left = _build_strategy("strategy-opaque-001")
    right = _build_strategy(" strategy-opaque-001 ")

    assert hash(left) == hash(right)


def test_strategy_is_usable_as_dictionary_key():
    key = _build_strategy()
    index = {key: "policy"}

    assert index[_build_strategy()] == "policy"


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_repr_contains_strategy_and_strategy_identity():
    representation = repr(_build_strategy())

    assert "Strategy(" in representation
    assert "StrategyIdentity(" in representation


def test_str_returns_deterministic_canonical_strategy_identity():
    strategy = Strategy(StrategyIdentity("  strategy-opaque-001  "))

    assert str(strategy) == "strategy-opaque-001"
    assert str(strategy) == str(_build_strategy())


# ---------------------------------------------------------------------------
# Mutability
# ---------------------------------------------------------------------------


def test_strategy_is_mutable():
    strategy = _build_strategy()
    replacement_identity = _build_identity("strategy-opaque-002")

    strategy.strategy_identity = replacement_identity

    assert strategy.strategy_identity is replacement_identity


def test_strategy_identity_remains_authoritative_after_mutation():
    strategy = _build_strategy("strategy-opaque-001")
    strategy.strategy_identity = _build_identity("strategy-opaque-002")

    assert strategy == _build_strategy("strategy-opaque-002")
    assert strategy != _build_strategy("strategy-opaque-001")


# ---------------------------------------------------------------------------
# Boundary Protection
# ---------------------------------------------------------------------------


def test_strategy_has_no_policy_or_external_context_fields():
    strategy = _build_strategy()

    assert not hasattr(strategy, "strategy_policy")
    assert not hasattr(strategy, "decision_policy")
    assert not hasattr(strategy, "signals")
    assert not hasattr(strategy, "recommendations")
    assert not hasattr(strategy, "allocation")
    assert not hasattr(strategy, "settlement")
    assert not hasattr(strategy, "accounting")


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_strategy_does_not_support_ordering():
    with pytest.raises(TypeError):
        _ = _build_strategy("strategy-opaque-001") < _build_strategy("strategy-opaque-002")


def test_strategy_aggregate_boundary_remains_intact():
    strategy = _build_strategy()

    assert strategy.strategy_identity is not None
    assert not hasattr(strategy, "portfolio")
    assert not hasattr(strategy, "trade")
    assert not hasattr(strategy, "order")


def test_strategy_has_no_invented_policy_semantics():
    strategy = _build_strategy()

    assert not hasattr(strategy, "policy")
    assert not hasattr(strategy, "lifecycle")
    assert strategy.strategy_identity.identity == "strategy-opaque-001"
