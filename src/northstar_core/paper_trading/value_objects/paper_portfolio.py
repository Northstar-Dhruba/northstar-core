"""Immutable holdings of one paper portfolio at one instant.

PaperPortfolio is a snapshot, not an account: it states what was held as of one
instant and nothing about how it came to be held. Folding a fill history into
one is orchestration and lives outside this value.

Positions are held in one canonical order so that two portfolios describing the
same holdings compare equal without either side re-sorting. That order is
required of the caller rather than imposed here: silently sorting would let a
malformed portfolio masquerade as canonical, and the producer -- which knows
how it assembled the holdings -- is the right place for the mistake to surface.

PaperPortfolio carries no cash, balance, buying power, realised or unrealised
profit and loss, margin or leverage, and offers no way to change what it holds.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.paper_trading.value_objects.paper_portfolio_identity import (
    PaperPortfolioIdentity,
)
from northstar_core.paper_trading.value_objects.position import Position


class InvalidPaperPortfolioError(ValidationError):
    """Raised when a PaperPortfolio value is invalid."""


def _order_key(position: Position) -> tuple[str, str]:
    """Return the canonical sort key: symbol, then exchange code."""
    listing_reference = position.listing_reference
    return (listing_reference.symbol.value, listing_reference.exchange_code.value)


def _validate_identity(value: PaperPortfolioIdentity) -> PaperPortfolioIdentity:
    if value is None:
        raise InvalidPaperPortfolioError("PaperPortfolio identity cannot be None.")
    if not isinstance(value, PaperPortfolioIdentity):
        raise InvalidPaperPortfolioError(
            "PaperPortfolio identity must be a PaperPortfolioIdentity value."
        )
    return value


def _validate_as_of(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidPaperPortfolioError("PaperPortfolio as-of instant cannot be None.")
    if not isinstance(value, PointInTime):
        raise InvalidPaperPortfolioError(
            "PaperPortfolio as-of instant must be a PointInTime value."
        )
    return value


def _validate_positions(value: tuple[Position, ...]) -> tuple[Position, ...]:
    if value is None:
        raise InvalidPaperPortfolioError("PaperPortfolio positions cannot be None.")
    if not isinstance(value, tuple):
        raise InvalidPaperPortfolioError("PaperPortfolio positions must be a tuple.")

    seen: set[tuple[str, str]] = set()
    previous: tuple[str, str] | None = None
    for position in value:
        if not isinstance(position, Position):
            raise InvalidPaperPortfolioError(
                "PaperPortfolio positions must contain Position values."
            )

        key = _order_key(position)
        if key in seen:
            raise InvalidPaperPortfolioError(
                "PaperPortfolio cannot contain two positions for one listing."
            )
        seen.add(key)

        if previous is not None and previous > key:
            raise InvalidPaperPortfolioError(
                "PaperPortfolio positions must be ordered by symbol, then exchange code."
            )
        previous = key

    return value


@dataclass(frozen=True, slots=True)
class PaperPortfolio:
    """Immutable holdings of one paper portfolio as of one instant.

    ``positions`` holds at most one Position per listing, ordered by symbol and
    then exchange code. A holding that is flat is absent rather than present at
    zero, because Position itself cannot be empty, so an empty portfolio is an
    empty tuple and is entirely valid.

    ``as_of`` records the instant the holdings describe. It comes from observed
    market evidence rather than a clock, so a snapshot stays reproducible.
    """

    identity: PaperPortfolioIdentity
    positions: tuple[Position, ...]
    as_of: PointInTime

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _validate_identity(self.identity))
        object.__setattr__(self, "positions", _validate_positions(self.positions))
        object.__setattr__(self, "as_of", _validate_as_of(self.as_of))

    @property
    def position_count(self) -> int:
        """Return how many listings are held."""
        return len(self.positions)

    def get_position(self, listing_reference: ListingReference) -> Position | None:
        """Return the holding in one listing, or None when none is held."""
        if listing_reference is None:
            raise InvalidPaperPortfolioError("PaperPortfolio listing reference cannot be None.")
        if not isinstance(listing_reference, ListingReference):
            raise InvalidPaperPortfolioError(
                "PaperPortfolio listing reference must be a ListingReference value."
            )

        for position in self.positions:
            if position.listing_reference == listing_reference:
                return position
        return None

    def __str__(self) -> str:
        return f"{self.identity} {self.as_of} positions={len(self.positions)}"

    def __repr__(self) -> str:
        return (
            "PaperPortfolio("
            f"identity={self.identity!r}, "
            f"positions={self.positions!r}, "
            f"as_of={self.as_of!r}"
            ")"
        )
