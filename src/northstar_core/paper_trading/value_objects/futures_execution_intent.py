"""Approved intent to execute one simulated futures trade.

FuturesExecutionIntent is the futures parallel of ExecutionIntent: which paper
portfolio would act, on which concrete futures contract, in which direction,
for how many whole contracts, on whose strategy advice, and at which decision
instant.

It is execution intent, not research evidence. It carries no recommendation
action, fill quotation, fill instant, provider identity, multiplier, margin or
profit and loss. A HOLD produces no intent, which OrderSide makes structurally
impossible to misrepresent.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.futures.value_objects.futures_contract import FuturesContract
from northstar_core.paper_trading.value_objects.futures_contract_count import (
    FuturesContractCount,
)
from northstar_core.paper_trading.value_objects.order_side import OrderSide
from northstar_core.paper_trading.value_objects.paper_portfolio_identity import (
    PaperPortfolioIdentity,
)
from northstar_core.strategy.value_objects.strategy_identity import StrategyIdentity


class InvalidFuturesExecutionIntentError(ValidationError):
    """Raised when a FuturesExecutionIntent value is invalid."""


def _validate_portfolio_identity(value: PaperPortfolioIdentity) -> PaperPortfolioIdentity:
    if value is None:
        raise InvalidFuturesExecutionIntentError(
            "FuturesExecutionIntent portfolio identity cannot be None."
        )
    if not isinstance(value, PaperPortfolioIdentity):
        raise InvalidFuturesExecutionIntentError(
            "FuturesExecutionIntent portfolio identity must be a PaperPortfolioIdentity value."
        )
    return value


def _validate_contract(value: FuturesContract) -> FuturesContract:
    if value is None:
        raise InvalidFuturesExecutionIntentError("FuturesExecutionIntent contract cannot be None.")
    if not isinstance(value, FuturesContract):
        raise InvalidFuturesExecutionIntentError(
            "FuturesExecutionIntent contract must be a FuturesContract value."
        )
    return value


def _validate_side(value: OrderSide) -> OrderSide:
    if value is None:
        raise InvalidFuturesExecutionIntentError("FuturesExecutionIntent side cannot be None.")
    if not isinstance(value, OrderSide):
        raise InvalidFuturesExecutionIntentError(
            "FuturesExecutionIntent side must be an OrderSide value."
        )
    return value


def _validate_contracts(value: FuturesContractCount) -> FuturesContractCount:
    if value is None:
        raise InvalidFuturesExecutionIntentError("FuturesExecutionIntent contracts cannot be None.")
    if not isinstance(value, FuturesContractCount):
        raise InvalidFuturesExecutionIntentError(
            "FuturesExecutionIntent contracts must be a FuturesContractCount value."
        )
    return value


def _validate_strategy_identity(value: StrategyIdentity) -> StrategyIdentity:
    if value is None:
        raise InvalidFuturesExecutionIntentError(
            "FuturesExecutionIntent strategy identity cannot be None."
        )
    if not isinstance(value, StrategyIdentity):
        raise InvalidFuturesExecutionIntentError(
            "FuturesExecutionIntent strategy identity must be a StrategyIdentity value."
        )
    return value


def _validate_decided_at(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidFuturesExecutionIntentError(
            "FuturesExecutionIntent decision instant cannot be None."
        )
    if not isinstance(value, PointInTime):
        raise InvalidFuturesExecutionIntentError(
            "FuturesExecutionIntent decision instant must be a PointInTime value."
        )
    return value


@dataclass(frozen=True, slots=True)
class FuturesExecutionIntent:
    """Immutable intent to execute one simulated futures trade.

    ``side`` is trade direction only. Whether a SELL reduces a long, opens a
    short or reverses through zero is decided by later execution policy.

    ``decided_at`` is the instant the advice was formed, taken from observed
    market evidence rather than a clock, so an intent remains reproducible.
    """

    portfolio_identity: PaperPortfolioIdentity
    contract: FuturesContract
    side: OrderSide
    contracts: FuturesContractCount
    strategy_identity: StrategyIdentity
    decided_at: PointInTime

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "portfolio_identity", _validate_portfolio_identity(self.portfolio_identity)
        )
        object.__setattr__(self, "contract", _validate_contract(self.contract))
        object.__setattr__(self, "side", _validate_side(self.side))
        object.__setattr__(self, "contracts", _validate_contracts(self.contracts))
        object.__setattr__(
            self, "strategy_identity", _validate_strategy_identity(self.strategy_identity)
        )
        object.__setattr__(self, "decided_at", _validate_decided_at(self.decided_at))

    def __str__(self) -> str:
        return (
            f"{self.side} {self.contracts} {self.contract} "
            f"{self.portfolio_identity} {self.strategy_identity} {self.decided_at}"
        )

    def __repr__(self) -> str:
        return (
            "FuturesExecutionIntent("
            f"portfolio_identity={self.portfolio_identity!r}, "
            f"contract={self.contract!r}, "
            f"side={self.side!r}, "
            f"contracts={self.contracts!r}, "
            f"strategy_identity={self.strategy_identity!r}, "
            f"decided_at={self.decided_at!r}"
            ")"
        )
