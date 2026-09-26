"""Approved intent to execute one simulated trade.

ExecutionIntent is the frozen bridge between research and paper execution: it
records which paper portfolio would act, on which listed asset, in which
direction, in what size, on whose strategy advice, and at which decision
instant.

An ExecutionIntent exists only where execution was actually intended. A HOLD
recommendation produces no intent at all, which OrderSide makes structurally
impossible to misrepresent. ExecutionIntent models no order type, time in
force, routing, commission, slippage, leverage, margin or position sizing
policy; deciding the quantity is the caller's concern, not this value's.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime, Quantity
from northstar_core.paper_trading.value_objects.order_side import OrderSide
from northstar_core.paper_trading.value_objects.paper_portfolio_identity import (
    PaperPortfolioIdentity,
)
from northstar_core.strategy.value_objects.strategy_identity import StrategyIdentity


class InvalidExecutionIntentError(ValidationError):
    """Raised when an ExecutionIntent value is invalid."""


def _validate_portfolio_identity(value: PaperPortfolioIdentity) -> PaperPortfolioIdentity:
    if value is None:
        raise InvalidExecutionIntentError("ExecutionIntent portfolio identity cannot be None.")
    if not isinstance(value, PaperPortfolioIdentity):
        raise InvalidExecutionIntentError(
            "ExecutionIntent portfolio identity must be a PaperPortfolioIdentity value."
        )
    return value


def _validate_listing_reference(value: ListingReference) -> ListingReference:
    if value is None:
        raise InvalidExecutionIntentError("ExecutionIntent listing reference cannot be None.")
    if not isinstance(value, ListingReference):
        raise InvalidExecutionIntentError(
            "ExecutionIntent listing reference must be a ListingReference value."
        )
    return value


def _validate_side(value: OrderSide) -> OrderSide:
    if value is None:
        raise InvalidExecutionIntentError("ExecutionIntent side cannot be None.")
    if not isinstance(value, OrderSide):
        raise InvalidExecutionIntentError("ExecutionIntent side must be an OrderSide value.")
    return value


def _validate_quantity(value: Quantity) -> Quantity:
    if value is None:
        raise InvalidExecutionIntentError("ExecutionIntent quantity cannot be None.")
    if not isinstance(value, Quantity):
        raise InvalidExecutionIntentError("ExecutionIntent quantity must be a Quantity value.")
    if value.value <= 0:
        raise InvalidExecutionIntentError("ExecutionIntent quantity must be greater than zero.")
    return value


def _validate_strategy_identity(value: StrategyIdentity) -> StrategyIdentity:
    if value is None:
        raise InvalidExecutionIntentError("ExecutionIntent strategy identity cannot be None.")
    if not isinstance(value, StrategyIdentity):
        raise InvalidExecutionIntentError(
            "ExecutionIntent strategy identity must be a StrategyIdentity value."
        )
    return value


def _validate_decided_at(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidExecutionIntentError("ExecutionIntent decision instant cannot be None.")
    if not isinstance(value, PointInTime):
        raise InvalidExecutionIntentError(
            "ExecutionIntent decision instant must be a PointInTime value."
        )
    return value


@dataclass(frozen=True, slots=True)
class ExecutionIntent:
    """Immutable intent to execute one simulated trade.

    ``decided_at`` is the instant the advice was formed, taken from observed
    market evidence rather than a clock, so an intent remains reproducible.

    A zero quantity is rejected rather than treated as a hold: an intent to
    trade nothing is not an intent, and allowing it would let a hold enter the
    execution path through the back door.
    """

    portfolio_identity: PaperPortfolioIdentity
    listing_reference: ListingReference
    side: OrderSide
    quantity: Quantity
    strategy_identity: StrategyIdentity
    decided_at: PointInTime

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "portfolio_identity", _validate_portfolio_identity(self.portfolio_identity)
        )
        object.__setattr__(
            self, "listing_reference", _validate_listing_reference(self.listing_reference)
        )
        object.__setattr__(self, "side", _validate_side(self.side))
        object.__setattr__(self, "quantity", _validate_quantity(self.quantity))
        object.__setattr__(
            self, "strategy_identity", _validate_strategy_identity(self.strategy_identity)
        )
        object.__setattr__(self, "decided_at", _validate_decided_at(self.decided_at))

    def __str__(self) -> str:
        return (
            f"{self.side} {self.quantity} {self.listing_reference} "
            f"{self.portfolio_identity} {self.strategy_identity} {self.decided_at}"
        )

    def __repr__(self) -> str:
        return (
            "ExecutionIntent("
            f"portfolio_identity={self.portfolio_identity!r}, "
            f"listing_reference={self.listing_reference!r}, "
            f"side={self.side!r}, "
            f"quantity={self.quantity!r}, "
            f"strategy_identity={self.strategy_identity!r}, "
            f"decided_at={self.decided_at!r}"
            ")"
        )
