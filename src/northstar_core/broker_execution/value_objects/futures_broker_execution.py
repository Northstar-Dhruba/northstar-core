"""One execution a broker reported against a Northstar futures order.

A FuturesBrokerExecution is an external fact: the broker's execution identifier,
the broker order it belongs to, how many whole contracts executed, at what
price, and when. Northstar never constructs one to represent a simulated fill.
Simulated fills are FuturesPaperFill, a different type in a different package.

Like FuturesPaperFill, the execution carries its own order, so account,
contract and side are always recoverable from it and are surfaced as derived
properties rather than duplicated. Unlike a paper fill, one order may have
several executions: a partial execution is an ordinary fact here, so the count
need not equal the requested count, but it can never exceed it. Whether the
executions of one order together exceed it is a question across executions,
answered where they are gathered, not by one value.

Timing
------
``executed_at`` must be strictly after the intent's decision instant, compared
with PointInTime.compare(). A decision instant is the completion of the session
decided upon, and an order can only reach a broker after that decision has been
frozen from the completed session, so a genuine execution is always later.
PointInTime is canonical UTC at up to microsecond precision; broker clocks and
coarser broker timestamps change neither of those facts.

``price`` is a QuoteValue in the product's own quotation convention. Converting
from a broker's price convention is Infrastructure's job, never this value's.
There is no commission, fee, liquidity flag, venue, currency, multiplier or
profit and loss.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.broker_execution.value_objects.broker_account_reference import (
    BrokerAccountReference,
)
from northstar_core.broker_execution.value_objects.broker_execution_id import (
    BrokerExecutionId,
)
from northstar_core.broker_execution.value_objects.broker_order_id import BrokerOrderId
from northstar_core.broker_execution.value_objects.futures_broker_order import (
    FuturesBrokerOrder,
)
from northstar_core.derivatives.value_objects import QuoteValue
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.futures.value_objects.futures_contract import FuturesContract
from northstar_core.paper_trading.value_objects.futures_contract_count import (
    FuturesContractCount,
)
from northstar_core.paper_trading.value_objects.order_side import OrderSide


class InvalidFuturesBrokerExecutionError(ValidationError):
    """Raised when a FuturesBrokerExecution value is invalid."""


def _validate_identity(value: BrokerExecutionId) -> BrokerExecutionId:
    if value is None:
        raise InvalidFuturesBrokerExecutionError("FuturesBrokerExecution identity cannot be None.")
    if not isinstance(value, BrokerExecutionId):
        raise InvalidFuturesBrokerExecutionError(
            "FuturesBrokerExecution identity must be a BrokerExecutionId value."
        )
    return value


def _validate_order(value: FuturesBrokerOrder) -> FuturesBrokerOrder:
    if value is None:
        raise InvalidFuturesBrokerExecutionError("FuturesBrokerExecution order cannot be None.")
    if not isinstance(value, FuturesBrokerOrder):
        raise InvalidFuturesBrokerExecutionError(
            "FuturesBrokerExecution order must be a FuturesBrokerOrder value."
        )
    return value


def _validate_broker_order_id(value: BrokerOrderId) -> BrokerOrderId:
    if value is None:
        raise InvalidFuturesBrokerExecutionError(
            "FuturesBrokerExecution broker order id cannot be None."
        )
    if not isinstance(value, BrokerOrderId):
        raise InvalidFuturesBrokerExecutionError(
            "FuturesBrokerExecution broker order id must be a BrokerOrderId value."
        )
    return value


def _validate_contracts(value: FuturesContractCount) -> FuturesContractCount:
    if value is None:
        raise InvalidFuturesBrokerExecutionError("FuturesBrokerExecution contracts cannot be None.")
    if not isinstance(value, FuturesContractCount):
        raise InvalidFuturesBrokerExecutionError(
            "FuturesBrokerExecution contracts must be a FuturesContractCount value."
        )
    return value


def _validate_price(value: QuoteValue) -> QuoteValue:
    if value is None:
        raise InvalidFuturesBrokerExecutionError("FuturesBrokerExecution price cannot be None.")
    if not isinstance(value, QuoteValue):
        raise InvalidFuturesBrokerExecutionError(
            "FuturesBrokerExecution price must be a QuoteValue value."
        )
    return value


def _validate_executed_at(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidFuturesBrokerExecutionError(
            "FuturesBrokerExecution execution instant cannot be None."
        )
    if not isinstance(value, PointInTime):
        raise InvalidFuturesBrokerExecutionError(
            "FuturesBrokerExecution execution instant must be a PointInTime value."
        )
    return value


@dataclass(frozen=True, slots=True)
class FuturesBrokerExecution:
    """Immutable broker-reported execution against one Northstar futures order.

    ``contracts`` may be fewer than the order requested but never more.
    ``executed_at`` must be strictly after the decision instant.
    """

    identity: BrokerExecutionId
    order: FuturesBrokerOrder
    broker_order_id: BrokerOrderId
    contracts: FuturesContractCount
    price: QuoteValue
    executed_at: PointInTime

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _validate_identity(self.identity))
        object.__setattr__(self, "order", _validate_order(self.order))
        object.__setattr__(self, "broker_order_id", _validate_broker_order_id(self.broker_order_id))
        object.__setattr__(self, "contracts", _validate_contracts(self.contracts))
        object.__setattr__(self, "price", _validate_price(self.price))
        object.__setattr__(self, "executed_at", _validate_executed_at(self.executed_at))

        if self.contracts.value > self.order.intent.contracts.value:
            raise InvalidFuturesBrokerExecutionError(
                "FuturesBrokerExecution contracts cannot exceed the order's requested contracts."
            )
        if self.executed_at.compare(self.order.intent.decided_at) <= 0:
            raise InvalidFuturesBrokerExecutionError(
                "FuturesBrokerExecution execution instant must be strictly after the intent "
                "decision instant."
            )

    @property
    def account(self) -> BrokerAccountReference:
        """Return the broker account this execution belongs to."""
        return self.order.intent.account

    @property
    def contract(self) -> FuturesContract:
        """Return the futures contract this execution transacted."""
        return self.order.intent.contract

    @property
    def side(self) -> OrderSide:
        """Return the direction this execution transacted."""
        return self.order.intent.side

    def __str__(self) -> str:
        return (
            f"{self.identity} {self.order.identity} {self.broker_order_id} {self.side} "
            f"{self.contracts} {self.contract} @ {self.price} {self.executed_at}"
        )

    def __repr__(self) -> str:
        return (
            "FuturesBrokerExecution("
            f"identity={self.identity!r}, "
            f"order={self.order!r}, "
            f"broker_order_id={self.broker_order_id!r}, "
            f"contracts={self.contracts!r}, "
            f"price={self.price!r}, "
            f"executed_at={self.executed_at!r}"
            ")"
        )
