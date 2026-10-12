"""The scope and session of one candidate selection.

- ``session_close`` is the completion instant of the selection session: the
  latest final session for which candidates are selected. Only decisions made
  exactly at it qualify. It is a trusted caller-supplied temporal contract:
  Application resolves it from the trading-session calendar and the finality
  policy (FG-9), and Core cannot verify that it is final.
- ``products`` are the approved futures products, for example NIFTY@NSE.
- ``strategies`` are the approved strategies whose research may become
  recommendations.

Both sets are given as tuples without duplicates and are stored in canonical
sorted order, so equal criteria are equal values whatever order they arrive in.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.futures import FuturesProductReference
from northstar_core.strategy import StrategyIdentity


class InvalidFuturesCandidateSelectionCriteriaError(ValidationError):
    """Raised when a FuturesCandidateSelectionCriteria value is invalid."""


def _validate_session_close(value: PointInTime) -> PointInTime:
    if not isinstance(value, PointInTime):
        raise InvalidFuturesCandidateSelectionCriteriaError(
            "FuturesCandidateSelectionCriteria session close must be a PointInTime value."
        )
    return value


def _canonical_products(
    value: tuple[FuturesProductReference, ...],
) -> tuple[FuturesProductReference, ...]:
    if not isinstance(value, tuple):
        raise InvalidFuturesCandidateSelectionCriteriaError(
            "FuturesCandidateSelectionCriteria products must be a tuple."
        )
    if not value:
        raise InvalidFuturesCandidateSelectionCriteriaError(
            "FuturesCandidateSelectionCriteria must approve at least one product."
        )
    if not all(isinstance(product, FuturesProductReference) for product in value):
        raise InvalidFuturesCandidateSelectionCriteriaError(
            "FuturesCandidateSelectionCriteria products must be FuturesProductReference values."
        )
    if len(set(value)) != len(value):
        raise InvalidFuturesCandidateSelectionCriteriaError(
            "FuturesCandidateSelectionCriteria products cannot repeat."
        )
    return tuple(sorted(value))


def _canonical_strategies(value: tuple[StrategyIdentity, ...]) -> tuple[StrategyIdentity, ...]:
    if not isinstance(value, tuple):
        raise InvalidFuturesCandidateSelectionCriteriaError(
            "FuturesCandidateSelectionCriteria strategies must be a tuple."
        )
    if not value:
        raise InvalidFuturesCandidateSelectionCriteriaError(
            "FuturesCandidateSelectionCriteria must approve at least one strategy."
        )
    if not all(isinstance(strategy, StrategyIdentity) for strategy in value):
        raise InvalidFuturesCandidateSelectionCriteriaError(
            "FuturesCandidateSelectionCriteria strategies must be StrategyIdentity values."
        )
    if len(set(value)) != len(value):
        raise InvalidFuturesCandidateSelectionCriteriaError(
            "FuturesCandidateSelectionCriteria strategies cannot repeat."
        )
    return tuple(sorted(value, key=lambda strategy: strategy.identity))


@dataclass(frozen=True, slots=True)
class FuturesCandidateSelectionCriteria:
    """Immutable selection session close, approved products and approved strategies."""

    session_close: PointInTime
    products: tuple[FuturesProductReference, ...]
    strategies: tuple[StrategyIdentity, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "session_close", _validate_session_close(self.session_close))
        object.__setattr__(self, "products", _canonical_products(self.products))
        object.__setattr__(self, "strategies", _canonical_strategies(self.strategies))

    def __str__(self) -> str:
        products = ", ".join(str(product) for product in self.products)
        strategies = ", ".join(str(strategy) for strategy in self.strategies)
        return f"session {self.session_close}; products {products}; strategies {strategies}"

    def __repr__(self) -> str:
        return (
            "FuturesCandidateSelectionCriteria("
            f"session_close={self.session_close!r}, "
            f"products={self.products!r}, "
            f"strategies={self.strategies!r}"
            ")"
        )
