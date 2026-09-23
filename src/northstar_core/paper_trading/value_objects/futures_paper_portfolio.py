"""Immutable futures holdings of one paper portfolio at one instant.

FuturesPaperPortfolio is the futures parallel of PaperPortfolio: a snapshot of
what was held as of one instant, not an account and not a fill history.

A futures paper portfolio belongs to exactly one strategy simulation, so that
StrategyIdentity is stored explicitly rather than inferred from fills: an
empty portfolio must still say which simulation it belongs to. Rejecting fills
from another portfolio or strategy is the job of the later fold, not of this
value.

Positions are keyed by concrete FuturesContract. Different expiries of one
product are independent holdings; nothing here rolls or merges them. As with
PaperPortfolio, canonical order is required of the caller rather than imposed,
so a malformed portfolio cannot masquerade as canonical.

There is no cash, margin, multiplier, notional or profit and loss, and no way
to change what the portfolio holds.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.derivatives.value_objects import ExpirationDate
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.futures.value_objects.futures_contract import FuturesContract
from northstar_core.futures.value_objects.futures_product_reference import (
    FuturesProductReference,
)
from northstar_core.paper_trading.value_objects.futures_position import FuturesPosition
from northstar_core.paper_trading.value_objects.paper_portfolio_identity import (
    PaperPortfolioIdentity,
)
from northstar_core.strategy.value_objects.strategy_identity import StrategyIdentity


class InvalidFuturesPaperPortfolioError(ValidationError):
    """Raised when a FuturesPaperPortfolio value is invalid."""


def _validate_identity(value: PaperPortfolioIdentity) -> PaperPortfolioIdentity:
    if value is None:
        raise InvalidFuturesPaperPortfolioError("FuturesPaperPortfolio identity cannot be None.")
    if not isinstance(value, PaperPortfolioIdentity):
        raise InvalidFuturesPaperPortfolioError(
            "FuturesPaperPortfolio identity must be a PaperPortfolioIdentity value."
        )
    return value


def _validate_strategy_identity(value: StrategyIdentity) -> StrategyIdentity:
    if value is None:
        raise InvalidFuturesPaperPortfolioError(
            "FuturesPaperPortfolio strategy identity cannot be None."
        )
    if not isinstance(value, StrategyIdentity):
        raise InvalidFuturesPaperPortfolioError(
            "FuturesPaperPortfolio strategy identity must be a StrategyIdentity value."
        )
    return value


def _validate_as_of(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidFuturesPaperPortfolioError(
            "FuturesPaperPortfolio as-of instant cannot be None."
        )
    if not isinstance(value, PointInTime):
        raise InvalidFuturesPaperPortfolioError(
            "FuturesPaperPortfolio as-of instant must be a PointInTime value."
        )
    return value


def _validate_positions(value: tuple[FuturesPosition, ...]) -> tuple[FuturesPosition, ...]:
    if value is None:
        raise InvalidFuturesPaperPortfolioError("FuturesPaperPortfolio positions cannot be None.")
    if not isinstance(value, tuple):
        raise InvalidFuturesPaperPortfolioError("FuturesPaperPortfolio positions must be a tuple.")

    seen: set[FuturesContract] = set()
    previous: tuple[FuturesProductReference, ExpirationDate] | None = None
    for position in value:
        if not isinstance(position, FuturesPosition):
            raise InvalidFuturesPaperPortfolioError(
                "FuturesPaperPortfolio positions must contain FuturesPosition values."
            )

        if position.contract in seen:
            raise InvalidFuturesPaperPortfolioError(
                "FuturesPaperPortfolio cannot contain two positions for one contract."
            )
        seen.add(position.contract)

        key = position.contract.natural_key
        if previous is not None and previous > key:
            raise InvalidFuturesPaperPortfolioError(
                "FuturesPaperPortfolio positions must be ordered by product, then expiration date."
            )
        previous = key

    return value


@dataclass(frozen=True, slots=True)
class FuturesPaperPortfolio:
    """Immutable futures holdings of one paper portfolio as of one instant.

    ``positions`` holds at most one FuturesPosition per contract, ordered by
    product (product code, then exchange code) and then expiration date. A flat
    contract is absent, so an empty portfolio is an empty tuple and is valid.

    ``as_of`` comes from observed market evidence rather than a clock.
    """

    identity: PaperPortfolioIdentity
    strategy_identity: StrategyIdentity
    positions: tuple[FuturesPosition, ...]
    as_of: PointInTime

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _validate_identity(self.identity))
        object.__setattr__(
            self, "strategy_identity", _validate_strategy_identity(self.strategy_identity)
        )
        object.__setattr__(self, "positions", _validate_positions(self.positions))
        object.__setattr__(self, "as_of", _validate_as_of(self.as_of))

    @property
    def position_count(self) -> int:
        """Return how many contracts are held."""
        return len(self.positions)

    def get_position(self, contract: FuturesContract) -> FuturesPosition | None:
        """Return the holding in one contract, or None when it is flat."""
        if contract is None:
            raise InvalidFuturesPaperPortfolioError(
                "FuturesPaperPortfolio contract cannot be None."
            )
        if not isinstance(contract, FuturesContract):
            raise InvalidFuturesPaperPortfolioError(
                "FuturesPaperPortfolio contract must be a FuturesContract value."
            )

        for position in self.positions:
            if position.contract == contract:
                return position
        return None

    def __str__(self) -> str:
        return (
            f"{self.identity} {self.strategy_identity} {self.as_of} positions={len(self.positions)}"
        )

    def __repr__(self) -> str:
        return (
            "FuturesPaperPortfolio("
            f"identity={self.identity!r}, "
            f"strategy_identity={self.strategy_identity!r}, "
            f"positions={self.positions!r}, "
            f"as_of={self.as_of!r}"
            ")"
        )
