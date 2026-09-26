"""Completed simulated execution of one paper order.

PaperFill records what a simulated execution actually did: how much was
transacted, at what price, and when. It is the only paper-trading fact worth
persisting, because every Position and portfolio valuation is a fold over
fills rather than independently held state.

A fill is therefore deliberately self-sufficient. It carries its own frozen
ExecutionIntent, so the portfolio, listed asset, direction, strategy and
decision instant a fill belongs to can always be recovered from the fill alone,
without joining against an order that may not have been retained. Those values
are surfaced as derived properties rather than duplicated as fields, so a fill
can never disagree with the intent it executed.

PaperFill models no commission, slippage, settlement, tax lot, realised profit
and loss, or broker acknowledgement.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime, Price, Quantity
from northstar_core.paper_trading.value_objects.execution_intent import ExecutionIntent
from northstar_core.paper_trading.value_objects.order_side import OrderSide
from northstar_core.paper_trading.value_objects.paper_fill_identity import PaperFillIdentity
from northstar_core.paper_trading.value_objects.paper_order_identity import PaperOrderIdentity
from northstar_core.paper_trading.value_objects.paper_portfolio_identity import (
    PaperPortfolioIdentity,
)
from northstar_core.strategy.value_objects.strategy_identity import StrategyIdentity


class InvalidPaperFillError(ValidationError):
    """Raised when a PaperFill value is invalid."""


def _validate_identity(value: PaperFillIdentity) -> PaperFillIdentity:
    if value is None:
        raise InvalidPaperFillError("PaperFill identity cannot be None.")
    if not isinstance(value, PaperFillIdentity):
        raise InvalidPaperFillError("PaperFill identity must be a PaperFillIdentity value.")
    return value


def _validate_order_identity(value: PaperOrderIdentity) -> PaperOrderIdentity:
    if value is None:
        raise InvalidPaperFillError("PaperFill order identity cannot be None.")
    if not isinstance(value, PaperOrderIdentity):
        raise InvalidPaperFillError("PaperFill order identity must be a PaperOrderIdentity value.")
    return value


def _validate_intent(value: ExecutionIntent) -> ExecutionIntent:
    if value is None:
        raise InvalidPaperFillError("PaperFill intent cannot be None.")
    if not isinstance(value, ExecutionIntent):
        raise InvalidPaperFillError("PaperFill intent must be an ExecutionIntent value.")
    return value


def _validate_quantity(value: Quantity) -> Quantity:
    if value is None:
        raise InvalidPaperFillError("PaperFill quantity cannot be None.")
    if not isinstance(value, Quantity):
        raise InvalidPaperFillError("PaperFill quantity must be a Quantity value.")
    if value.value <= 0:
        raise InvalidPaperFillError("PaperFill quantity must be greater than zero.")
    return value


def _validate_price(value: Price) -> Price:
    if value is None:
        raise InvalidPaperFillError("PaperFill price cannot be None.")
    if not isinstance(value, Price):
        raise InvalidPaperFillError("PaperFill price must be a Price value.")
    if value.amount <= 0:
        raise InvalidPaperFillError("PaperFill price must be greater than zero.")
    return value


def _validate_filled_at(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidPaperFillError("PaperFill fill instant cannot be None.")
    if not isinstance(value, PointInTime):
        raise InvalidPaperFillError("PaperFill fill instant must be a PointInTime value.")
    return value


@dataclass(frozen=True, slots=True)
class PaperFill:
    """Immutable completed execution of one simulated paper order.

    ``quantity`` must equal the intended quantity: partial fills are not
    representable yet, so a fill either executed the whole intent or does not
    exist. ``filled_at`` may equal the decision instant -- simulated execution
    against decision-time evidence has no delay -- but may never precede it,
    which is checked with PointInTime.compare() so offset-equivalent instants
    are judged chronologically rather than by their text.
    """

    identity: PaperFillIdentity
    order_identity: PaperOrderIdentity
    intent: ExecutionIntent
    quantity: Quantity
    price: Price
    filled_at: PointInTime

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _validate_identity(self.identity))
        object.__setattr__(self, "order_identity", _validate_order_identity(self.order_identity))
        object.__setattr__(self, "intent", _validate_intent(self.intent))
        object.__setattr__(self, "quantity", _validate_quantity(self.quantity))
        object.__setattr__(self, "price", _validate_price(self.price))
        object.__setattr__(self, "filled_at", _validate_filled_at(self.filled_at))

        if self.quantity != self.intent.quantity:
            raise InvalidPaperFillError(
                "PaperFill quantity must equal the intended quantity; "
                "partial fills are not supported."
            )
        if self.filled_at.compare(self.intent.decided_at) < 0:
            raise InvalidPaperFillError(
                "PaperFill fill instant cannot precede the intent decision instant."
            )

    @property
    def portfolio_identity(self) -> PaperPortfolioIdentity:
        """Return the paper portfolio this fill belongs to."""
        return self.intent.portfolio_identity

    @property
    def listing_reference(self) -> ListingReference:
        """Return the listed asset this fill transacted."""
        return self.intent.listing_reference

    @property
    def side(self) -> OrderSide:
        """Return the direction this fill executed."""
        return self.intent.side

    @property
    def strategy_identity(self) -> StrategyIdentity:
        """Return the strategy whose advice this fill executed."""
        return self.intent.strategy_identity

    @property
    def decided_at(self) -> PointInTime:
        """Return the instant the executed advice was formed."""
        return self.intent.decided_at

    def __str__(self) -> str:
        return (
            f"{self.identity} {self.order_identity} {self.side} "
            f"{self.quantity} @ {self.price} {self.filled_at}"
        )

    def __repr__(self) -> str:
        return (
            "PaperFill("
            f"identity={self.identity!r}, "
            f"order_identity={self.order_identity!r}, "
            f"intent={self.intent!r}, "
            f"quantity={self.quantity!r}, "
            f"price={self.price!r}, "
            f"filled_at={self.filled_at!r}"
            ")"
        )
