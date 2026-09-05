"""Reference Strategy aggregate root.

Strategy is a mutable decision-policy aggregate root. Version 1.0 composes
only StrategyIdentity; Market Data, Portfolio, Trades, and Orders remain
external contexts consumed or influenced by Strategy.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.strategy.value_objects import StrategyIdentity


class InvalidStrategyError(ValidationError):
    """Raised when a Strategy aggregate is invalid."""


def _validate_strategy_identity(value: StrategyIdentity) -> StrategyIdentity:
    if value is None:
        raise InvalidStrategyError("Strategy identity cannot be None.")
    if not isinstance(value, StrategyIdentity):
        raise InvalidStrategyError("Strategy identity must be a StrategyIdentity value.")
    return value


@dataclass(slots=True, eq=False)
class Strategy:
    """Reference Aggregate Root for the Strategy bounded context.

    Strategy owns decision policy, strategy consistency, and strategy lifecycle.
    Version 1.0 deliberately introduces no policy representation, workflow,
    execution, risk, performance, or consumed-context composition.
    """

    strategy_identity: StrategyIdentity

    def __post_init__(self) -> None:
        self.strategy_identity = _validate_strategy_identity(self.strategy_identity)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Strategy):
            return NotImplemented
        return self.strategy_identity == other.strategy_identity

    def __hash__(self) -> int:
        return hash(self.strategy_identity)

    def __str__(self) -> str:
        return str(self.strategy_identity)

    def __repr__(self) -> str:
        return f"Strategy(strategy_identity={self.strategy_identity!r})"
