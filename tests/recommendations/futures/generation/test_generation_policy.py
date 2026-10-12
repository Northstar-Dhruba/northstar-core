"""Tests for the versioned futures recommendation-generation policy (ADR-018).

All values are synthetic, non-production calibration fixtures.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal

import pytest

from northstar_core.recommendations.futures import (
    FuturesRecommendationGenerationPolicy,
    InvalidFuturesRecommendationGenerationPolicyError,
    RecommendationPolicyVersion,
)
from northstar_core.strategy import StrategyIdentity

_STRATEGY = StrategyIdentity("synthetic-directional-v1")
_VALID: dict[str, object] = {
    "version": RecommendationPolicyVersion("f4-synthetic-fixture-v1"),
    "approved_strategies": (_STRATEGY,),
    "lookback_changes": 19,
    "entry_multiplier": Decimal("0.25"),
    "stop_multiplier": Decimal("1.5"),
    "target_multiplier": Decimal("3"),
    "price_increment": Decimal("0.05"),
    "min_reward_to_risk": Decimal("1.5"),
    "short_enabled": True,
}


def _policy(**overrides: object) -> FuturesRecommendationGenerationPolicy:
    return FuturesRecommendationGenerationPolicy(**{**_VALID, **overrides})  # type: ignore[arg-type]


def test_constructs_a_valid_policy_and_preserves_every_value() -> None:
    policy = _policy()

    assert policy.version == RecommendationPolicyVersion("f4-synthetic-fixture-v1")
    assert policy.approved_strategies == (_STRATEGY,)
    assert policy.strategy == _STRATEGY
    assert policy.lookback_changes == 19
    assert policy.entry_multiplier == Decimal("0.25")
    assert policy.stop_multiplier == Decimal("1.5")
    assert policy.target_multiplier == Decimal("3")
    assert policy.price_increment == Decimal("0.05")
    assert policy.min_reward_to_risk == Decimal("1.5")
    assert policy.short_enabled is True


def test_every_parameter_is_required() -> None:
    for name in _VALID:
        arguments = {key: value for key, value in _VALID.items() if key != name}
        with pytest.raises(TypeError):
            FuturesRecommendationGenerationPolicy(**arguments)  # type: ignore[arg-type]


def test_a_zero_entry_multiplier_is_allowed() -> None:
    assert _policy(entry_multiplier=Decimal("0")).entry_multiplier == 0


@pytest.mark.parametrize(
    "field_name, value",
    [
        ("entry_multiplier", Decimal("-0.01")),
        ("stop_multiplier", Decimal("0")),
        ("stop_multiplier", Decimal("-1")),
        ("target_multiplier", Decimal("0")),
        ("target_multiplier", Decimal("-1")),
        ("price_increment", Decimal("0")),
        ("price_increment", Decimal("-0.05")),
        ("min_reward_to_risk", Decimal("0")),
        ("min_reward_to_risk", Decimal("-1.5")),
    ],
)
def test_rejects_out_of_range_numeric_parameters(field_name: str, value: Decimal) -> None:
    with pytest.raises(InvalidFuturesRecommendationGenerationPolicyError):
        _policy(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "entry_multiplier",
        "stop_multiplier",
        "target_multiplier",
        "price_increment",
        "min_reward_to_risk",
    ],
)
@pytest.mark.parametrize(
    "value",
    [1.5, 2, "1.5", True, None, Decimal("NaN"), Decimal("Infinity")],
    ids=["float", "int", "str", "bool", "none", "nan", "infinity"],
)
def test_rejects_non_decimal_and_non_finite_parameters(field_name: str, value: object) -> None:
    with pytest.raises(InvalidFuturesRecommendationGenerationPolicyError):
        _policy(**{field_name: value})


@pytest.mark.parametrize("value", [18, 20, 0, -19, True, 19.0, "19", Decimal("19")])
def test_v1_lookback_is_exactly_nineteen_integer_changes(value: object) -> None:
    with pytest.raises(InvalidFuturesRecommendationGenerationPolicyError):
        _policy(lookback_changes=value)


@pytest.mark.parametrize(
    "value",
    [
        (),
        [_STRATEGY],
        ("synthetic-directional-v1",),
        (_STRATEGY, _STRATEGY),
        (_STRATEGY, StrategyIdentity("synthetic-second-v1")),
    ],
    ids=["empty", "list", "wrong-type", "duplicate", "two-strategies"],
)
def test_v1_approves_exactly_one_strategy(value: object) -> None:
    with pytest.raises(InvalidFuturesRecommendationGenerationPolicyError):
        _policy(approved_strategies=value)


@pytest.mark.parametrize("value", [1, "true", None])
def test_short_enabled_must_be_a_bool(value: object) -> None:
    with pytest.raises(InvalidFuturesRecommendationGenerationPolicyError):
        _policy(short_enabled=value)


def test_the_version_must_be_a_policy_version() -> None:
    with pytest.raises(InvalidFuturesRecommendationGenerationPolicyError):
        _policy(version="f4-synthetic-fixture-v1")


def test_the_policy_is_immutable() -> None:
    policy = _policy()

    with pytest.raises(dataclasses.FrozenInstanceError):
        policy.short_enabled = False  # type: ignore[misc]


def test_equal_parameters_make_equal_and_equally_hashed_policies() -> None:
    first = _policy(min_reward_to_risk=Decimal("1.5"))
    second = _policy(min_reward_to_risk=Decimal("1.50"))

    assert first == second
    assert hash(first) == hash(second)


def test_a_changed_parameter_is_a_different_policy() -> None:
    assert _policy() != _policy(short_enabled=False)
    assert _policy() != _policy(version=RecommendationPolicyVersion("f4-synthetic-fixture-v2"))


def test_str_names_the_version_and_strategy() -> None:
    assert str(_policy()) == "policy f4-synthetic-fixture-v1 for synthetic-directional-v1"
