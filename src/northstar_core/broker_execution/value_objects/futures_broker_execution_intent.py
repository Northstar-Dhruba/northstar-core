"""Approved intent to execute one futures trade through a broker account.

FuturesBrokerExecutionIntent is the broker parallel of FuturesExecutionIntent:
which broker account would act, on which concrete futures contract, in which
direction, for how many whole contracts, on whose strategy advice, and at which
decision instant.

It is deliberately a distinct type rather than a generalized
FuturesExecutionIntent. The paper intent names a PaperPortfolioIdentity and
describes a simulated trade; this one names a BrokerAccountReference and
describes a trade a broker will execute. Keeping them apart means a paper intent
can never be submitted to a broker and a broker intent can never be stored as a
simulated order. The shared vocabulary -- contract, side, count, strategy and
instant -- is reused, not duplicated.

It is execution intent, not a broker fact. It carries no recommendation action,
broker order identifier, status, execution, price, provider symbol, order type
or time in force. A HOLD produces no intent, which OrderSide makes structurally
impossible to misrepresent.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.broker_execution.value_objects.broker_account_reference import (
    BrokerAccountReference,
)
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.futures.value_objects.futures_contract import FuturesContract
from northstar_core.paper_trading.value_objects.futures_contract_count import (
    FuturesContractCount,
)
from northstar_core.paper_trading.value_objects.order_side import OrderSide
from northstar_core.strategy.value_objects.strategy_identity import StrategyIdentity


class InvalidFuturesBrokerExecutionIntentError(ValidationError):
    """Raised when a FuturesBrokerExecutionIntent value is invalid."""


def _validate_account(value: BrokerAccountReference) -> BrokerAccountReference:
    if value is None:
        raise InvalidFuturesBrokerExecutionIntentError(
            "FuturesBrokerExecutionIntent account cannot be None."
        )
    if not isinstance(value, BrokerAccountReference):
        raise InvalidFuturesBrokerExecutionIntentError(
            "FuturesBrokerExecutionIntent account must be a BrokerAccountReference value."
        )
    return value


def _validate_contract(value: FuturesContract) -> FuturesContract:
    if value is None:
        raise InvalidFuturesBrokerExecutionIntentError(
            "FuturesBrokerExecutionIntent contract cannot be None."
        )
    if not isinstance(value, FuturesContract):
        raise InvalidFuturesBrokerExecutionIntentError(
            "FuturesBrokerExecutionIntent contract must be a FuturesContract value."
        )
    return value


def _validate_side(value: OrderSide) -> OrderSide:
    if value is None:
        raise InvalidFuturesBrokerExecutionIntentError(
            "FuturesBrokerExecutionIntent side cannot be None."
        )
    if not isinstance(value, OrderSide):
        raise InvalidFuturesBrokerExecutionIntentError(
            "FuturesBrokerExecutionIntent side must be an OrderSide value."
        )
    return value


def _validate_contracts(value: FuturesContractCount) -> FuturesContractCount:
    if value is None:
        raise InvalidFuturesBrokerExecutionIntentError(
            "FuturesBrokerExecutionIntent contracts cannot be None."
        )
    if not isinstance(value, FuturesContractCount):
        raise InvalidFuturesBrokerExecutionIntentError(
            "FuturesBrokerExecutionIntent contracts must be a FuturesContractCount value."
        )
    return value


def _validate_strategy_identity(value: StrategyIdentity) -> StrategyIdentity:
    if value is None:
        raise InvalidFuturesBrokerExecutionIntentError(
            "FuturesBrokerExecutionIntent strategy identity cannot be None."
        )
    if not isinstance(value, StrategyIdentity):
        raise InvalidFuturesBrokerExecutionIntentError(
            "FuturesBrokerExecutionIntent strategy identity must be a StrategyIdentity value."
        )
    return value


def _validate_decided_at(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidFuturesBrokerExecutionIntentError(
            "FuturesBrokerExecutionIntent decision instant cannot be None."
        )
    if not isinstance(value, PointInTime):
        raise InvalidFuturesBrokerExecutionIntentError(
            "FuturesBrokerExecutionIntent decision instant must be a PointInTime value."
        )
    return value


@dataclass(frozen=True, slots=True)
class FuturesBrokerExecutionIntent:
    """Immutable intent to execute one futures trade through one broker account.

    ``side`` is trade direction only. Whether a SELL reduces a long, opens a
    short or reverses through zero was decided by the policy that produced the
    intent, not by this value.

    ``decided_at`` is the instant the advice was formed, taken from the frozen
    research decision rather than a clock.
    """

    account: BrokerAccountReference
    contract: FuturesContract
    side: OrderSide
    contracts: FuturesContractCount
    strategy_identity: StrategyIdentity
    decided_at: PointInTime

    def __post_init__(self) -> None:
        object.__setattr__(self, "account", _validate_account(self.account))
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
            f"{self.account} {self.strategy_identity} {self.decided_at}"
        )

    def __repr__(self) -> str:
        return (
            "FuturesBrokerExecutionIntent("
            f"account={self.account!r}, "
            f"contract={self.contract!r}, "
            f"side={self.side!r}, "
            f"contracts={self.contracts!r}, "
            f"strategy_identity={self.strategy_identity!r}, "
            f"decided_at={self.decided_at!r}"
            ")"
        )
