"""The versioned parameters of one recommendation-generation policy (ADR-018).

A policy names every material generation parameter under one
RecommendationPolicyVersion:

- ``approved_strategies`` -- the strategies whose candidates may become
  proposals. Futures V1 approves exactly one, supplied by the caller; no
  strategy name is assumed here.
- ``lookback_changes`` -- N, the number of close-to-close changes the movement
  unit averages. Futures V1 fixes N at 19, read from twenty closes.
- ``entry_multiplier`` (kE >= 0), ``stop_multiplier`` (kS > 0) and
  ``target_multiplier`` (kT > 0) -- distances in movement units.
- ``price_increment`` (T > 0) -- the grid every level is aligned to.
- ``min_reward_to_risk`` (> 0) -- the lowest acceptable worst-entry ratio.
- ``short_enabled`` -- whether SELL research may become a SHORT proposal.

Numeric parameters must be Decimal instances: a float, int, str or bool is
refused rather than converted, so no value changes on the way in. Nothing has
a default. A validated price increment is a caller statement, not evidence that
it matches the current exchange specification, and none of these values is an
approved production calibration.

Changing any parameter requires a new version. Core sees one policy at a time
and cannot detect a version reused with different parameters elsewhere; that is
a responsibility of a future Application policy registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.recommendations.futures.value_objects import RecommendationPolicyVersion
from northstar_core.strategy import StrategyIdentity

# Futures V1 decisions (ADR-018, F4-D2 and F4-D4).
_V1_LOOKBACK_CHANGES = 19
_V1_STRATEGY_COUNT = 1


class InvalidFuturesRecommendationGenerationPolicyError(ValidationError):
    """Raised when a FuturesRecommendationGenerationPolicy value is invalid."""


def _validate_version(value: RecommendationPolicyVersion) -> RecommendationPolicyVersion:
    if not isinstance(value, RecommendationPolicyVersion):
        raise InvalidFuturesRecommendationGenerationPolicyError(
            "FuturesRecommendationGenerationPolicy version must be a "
            "RecommendationPolicyVersion value."
        )
    return value


def _validate_strategies(value: tuple[StrategyIdentity, ...]) -> tuple[StrategyIdentity, ...]:
    if not isinstance(value, tuple):
        raise InvalidFuturesRecommendationGenerationPolicyError(
            "FuturesRecommendationGenerationPolicy approved strategies must be a tuple."
        )
    if not value:
        raise InvalidFuturesRecommendationGenerationPolicyError(
            "FuturesRecommendationGenerationPolicy must approve a strategy."
        )
    if not all(isinstance(strategy, StrategyIdentity) for strategy in value):
        raise InvalidFuturesRecommendationGenerationPolicyError(
            "FuturesRecommendationGenerationPolicy approved strategies must be "
            "StrategyIdentity values."
        )
    if len(set(value)) != len(value):
        raise InvalidFuturesRecommendationGenerationPolicyError(
            "FuturesRecommendationGenerationPolicy approved strategies cannot repeat."
        )
    if len(value) != _V1_STRATEGY_COUNT:
        raise InvalidFuturesRecommendationGenerationPolicyError(
            "Futures V1 generation approves exactly one strategy."
        )
    return value


def _validate_lookback(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidFuturesRecommendationGenerationPolicyError(
            "FuturesRecommendationGenerationPolicy lookback changes must be an integer."
        )
    if value < 1:
        raise InvalidFuturesRecommendationGenerationPolicyError(
            "FuturesRecommendationGenerationPolicy lookback changes must be positive."
        )
    if value != _V1_LOOKBACK_CHANGES:
        raise InvalidFuturesRecommendationGenerationPolicyError(
            f"Futures V1 generation uses exactly {_V1_LOOKBACK_CHANGES} lookback changes."
        )
    return value


def _validate_decimal(value: Decimal, field_name: str, *, allow_zero: bool) -> Decimal:
    if not isinstance(value, Decimal):
        raise InvalidFuturesRecommendationGenerationPolicyError(
            f"FuturesRecommendationGenerationPolicy {field_name} must be a Decimal."
        )
    if not value.is_finite():
        raise InvalidFuturesRecommendationGenerationPolicyError(
            f"FuturesRecommendationGenerationPolicy {field_name} must be finite."
        )
    if value < 0 or (value == 0 and not allow_zero):
        bound = "zero or greater" if allow_zero else "greater than zero"
        raise InvalidFuturesRecommendationGenerationPolicyError(
            f"FuturesRecommendationGenerationPolicy {field_name} must be {bound}."
        )
    return value


def _validate_short_enabled(value: bool) -> bool:
    if not isinstance(value, bool):
        raise InvalidFuturesRecommendationGenerationPolicyError(
            "FuturesRecommendationGenerationPolicy short enabled must be a bool."
        )
    return value


@dataclass(frozen=True, slots=True)
class FuturesRecommendationGenerationPolicy:
    """Immutable, versioned recommendation-generation parameters."""

    version: RecommendationPolicyVersion
    approved_strategies: tuple[StrategyIdentity, ...]
    lookback_changes: int
    entry_multiplier: Decimal
    stop_multiplier: Decimal
    target_multiplier: Decimal
    price_increment: Decimal
    min_reward_to_risk: Decimal
    short_enabled: bool

    def __post_init__(self) -> None:
        _validate_version(self.version)
        _validate_strategies(self.approved_strategies)
        _validate_lookback(self.lookback_changes)
        _validate_decimal(self.entry_multiplier, "entry multiplier", allow_zero=True)
        _validate_decimal(self.stop_multiplier, "stop multiplier", allow_zero=False)
        _validate_decimal(self.target_multiplier, "target multiplier", allow_zero=False)
        _validate_decimal(self.price_increment, "price increment", allow_zero=False)
        _validate_decimal(self.min_reward_to_risk, "minimum reward to risk", allow_zero=False)
        _validate_short_enabled(self.short_enabled)

    @property
    def strategy(self) -> StrategyIdentity:
        """Return the single strategy Futures V1 approves."""
        return self.approved_strategies[0]

    def __str__(self) -> str:
        return f"policy {self.version} for {self.strategy}"

    def __repr__(self) -> str:
        return (
            "FuturesRecommendationGenerationPolicy("
            f"version={self.version!r}, "
            f"approved_strategies={self.approved_strategies!r}, "
            f"lookback_changes={self.lookback_changes!r}, "
            f"entry_multiplier={self.entry_multiplier!r}, "
            f"stop_multiplier={self.stop_multiplier!r}, "
            f"target_multiplier={self.target_multiplier!r}, "
            f"price_increment={self.price_increment!r}, "
            f"min_reward_to_risk={self.min_reward_to_risk!r}, "
            f"short_enabled={self.short_enabled!r}"
            ")"
        )
