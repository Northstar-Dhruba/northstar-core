"""Completed simulated execution of one futures paper order.

FuturesPaperFill records what a simulated futures execution did: how many whole
contracts transacted, at what quotation, and when Northstar could establish
it. Like PaperFill it carries its own frozen intent, so the portfolio,
contract, direction, strategy and decision instant are always recoverable from
the fill alone and are surfaced as derived properties rather than duplicated.

Timing semantics
----------------
The simulated execution quotation is taken from the OPEN of the first stored
daily bar strictly after the decision. ``filled_at`` records that bar's
PointInTime -- its completion boundary, the instant at which canonical daily
data first makes the simulated fill knowable. It does not claim the trade
executed at that session's close. Because the fill bar is strictly after the
decision, ``filled_at`` must be strictly after ``decided_at``; this value checks
that ordering but does not select the bar.

The quotation is a QuoteValue in the product's own convention and may be
positive, zero or negative. There is no Price, Currency, Money, multiplier,
commission, slippage, margin or profit and loss, and no partial fill.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.derivatives.value_objects import QuoteValue
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.futures.value_objects.futures_contract import FuturesContract
from northstar_core.paper_trading.value_objects.futures_contract_count import (
    FuturesContractCount,
)
from northstar_core.paper_trading.value_objects.futures_execution_intent import (
    FuturesExecutionIntent,
)
from northstar_core.paper_trading.value_objects.order_side import OrderSide
from northstar_core.paper_trading.value_objects.paper_fill_identity import PaperFillIdentity
from northstar_core.paper_trading.value_objects.paper_order_identity import PaperOrderIdentity
from northstar_core.paper_trading.value_objects.paper_portfolio_identity import (
    PaperPortfolioIdentity,
)
from northstar_core.strategy.value_objects.strategy_identity import StrategyIdentity


class InvalidFuturesPaperFillError(ValidationError):
    """Raised when a FuturesPaperFill value is invalid."""


def _validate_identity(value: PaperFillIdentity) -> PaperFillIdentity:
    if value is None:
        raise InvalidFuturesPaperFillError("FuturesPaperFill identity cannot be None.")
    if not isinstance(value, PaperFillIdentity):
        raise InvalidFuturesPaperFillError(
            "FuturesPaperFill identity must be a PaperFillIdentity value."
        )
    return value


def _validate_order_identity(value: PaperOrderIdentity) -> PaperOrderIdentity:
    if value is None:
        raise InvalidFuturesPaperFillError("FuturesPaperFill order identity cannot be None.")
    if not isinstance(value, PaperOrderIdentity):
        raise InvalidFuturesPaperFillError(
            "FuturesPaperFill order identity must be a PaperOrderIdentity value."
        )
    return value


def _validate_intent(value: FuturesExecutionIntent) -> FuturesExecutionIntent:
    if value is None:
        raise InvalidFuturesPaperFillError("FuturesPaperFill intent cannot be None.")
    if not isinstance(value, FuturesExecutionIntent):
        raise InvalidFuturesPaperFillError(
            "FuturesPaperFill intent must be a FuturesExecutionIntent value."
        )
    return value


def _validate_contracts(value: FuturesContractCount) -> FuturesContractCount:
    if value is None:
        raise InvalidFuturesPaperFillError("FuturesPaperFill contracts cannot be None.")
    if not isinstance(value, FuturesContractCount):
        raise InvalidFuturesPaperFillError(
            "FuturesPaperFill contracts must be a FuturesContractCount value."
        )
    return value


def _validate_fill_quote(value: QuoteValue) -> QuoteValue:
    if value is None:
        raise InvalidFuturesPaperFillError("FuturesPaperFill fill quote cannot be None.")
    if not isinstance(value, QuoteValue):
        raise InvalidFuturesPaperFillError(
            "FuturesPaperFill fill quote must be a QuoteValue value."
        )
    return value


def _validate_filled_at(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidFuturesPaperFillError("FuturesPaperFill fill instant cannot be None.")
    if not isinstance(value, PointInTime):
        raise InvalidFuturesPaperFillError(
            "FuturesPaperFill fill instant must be a PointInTime value."
        )
    return value


@dataclass(frozen=True, slots=True)
class FuturesPaperFill:
    """Immutable completed execution of one simulated futures paper order.

    ``contracts`` must equal the intended count: a fill either executed the
    whole intent or does not exist. ``filled_at`` must be strictly after the
    decision instant, compared with PointInTime.compare() so offset-equivalent
    instants are judged chronologically rather than by their text.
    """

    identity: PaperFillIdentity
    order_identity: PaperOrderIdentity
    intent: FuturesExecutionIntent
    contracts: FuturesContractCount
    fill_quote: QuoteValue
    filled_at: PointInTime

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _validate_identity(self.identity))
        object.__setattr__(self, "order_identity", _validate_order_identity(self.order_identity))
        object.__setattr__(self, "intent", _validate_intent(self.intent))
        object.__setattr__(self, "contracts", _validate_contracts(self.contracts))
        object.__setattr__(self, "fill_quote", _validate_fill_quote(self.fill_quote))
        object.__setattr__(self, "filled_at", _validate_filled_at(self.filled_at))

        if self.contracts != self.intent.contracts:
            raise InvalidFuturesPaperFillError(
                "FuturesPaperFill contracts must equal the intended contracts; "
                "partial fills are not supported."
            )
        if self.filled_at.compare(self.intent.decided_at) <= 0:
            raise InvalidFuturesPaperFillError(
                "FuturesPaperFill fill instant must be strictly after the intent decision instant."
            )

    @property
    def portfolio_identity(self) -> PaperPortfolioIdentity:
        """Return the paper portfolio this fill belongs to."""
        return self.intent.portfolio_identity

    @property
    def contract(self) -> FuturesContract:
        """Return the futures contract this fill transacted."""
        return self.intent.contract

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
            f"{self.contracts} {self.contract} @ {self.fill_quote} {self.filled_at}"
        )

    def __repr__(self) -> str:
        return (
            "FuturesPaperFill("
            f"identity={self.identity!r}, "
            f"order_identity={self.order_identity!r}, "
            f"intent={self.intent!r}, "
            f"contracts={self.contracts!r}, "
            f"fill_quote={self.fill_quote!r}, "
            f"filled_at={self.filled_at!r}"
            ")"
        )
