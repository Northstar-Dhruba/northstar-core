"""Reference Portfolio aggregate root.

Portfolio preserves current ownership interpretation for one Participant at a
PointInTime. It owns a validated collection of Listing-specific Positions and
remains mutable as ownership interpretation evolves.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.domain.value_objects.participant_reference import ParticipantReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.portfolio.position import Position
from northstar_core.portfolio.value_objects import PortfolioIdentity


class InvalidPortfolioError(ValidationError):
    """Raised when a Portfolio aggregate is invalid."""


def _validate_portfolio_identity(value: PortfolioIdentity) -> PortfolioIdentity:
    if value is None:
        raise InvalidPortfolioError("Portfolio identity cannot be None.")
    if not isinstance(value, PortfolioIdentity):
        raise InvalidPortfolioError("Portfolio identity must be a PortfolioIdentity value.")
    return value


def _validate_participant_reference(value: ParticipantReference) -> ParticipantReference:
    if value is None:
        raise InvalidPortfolioError("Portfolio participant reference cannot be None.")
    if not isinstance(value, ParticipantReference):
        raise InvalidPortfolioError(
            "Portfolio participant reference must be a ParticipantReference value."
        )
    return value


def _validate_point_in_time(value: PointInTime) -> PointInTime:
    if value is None:
        raise InvalidPortfolioError("Portfolio point-in-time context cannot be None.")
    if not isinstance(value, PointInTime):
        raise InvalidPortfolioError("Portfolio point-in-time context must be a PointInTime value.")
    return value


def _validate_positions(value: object) -> tuple[Position, ...]:
    if value is None:
        raise InvalidPortfolioError("Portfolio positions cannot be None.")
    if not isinstance(value, tuple):
        raise InvalidPortfolioError("Portfolio positions must be a tuple of Position entities.")

    positions: list[Position] = []
    for position in value:
        if not isinstance(position, Position):
            raise InvalidPortfolioError("Portfolio positions must contain Position entities.")
        if any(existing.listing == position.listing for existing in positions):
            raise InvalidPortfolioError(
                "Portfolio cannot contain multiple Positions for the same Listing."
            )
        positions.append(position)

    return value


@dataclass(slots=True, eq=False)
class Portfolio:
    """Reference Aggregate Root for the Portfolio bounded context.

    Portfolio preserves current ownership interpretation for one Participant.
    It composes only the approved Portfolio concepts and owns zero or more
    Listing-specific Positions.
    """

    portfolio_identity: PortfolioIdentity
    participant_reference: ParticipantReference
    point_in_time: PointInTime
    positions: tuple[Position, ...]

    def __post_init__(self) -> None:
        self.portfolio_identity = _validate_portfolio_identity(self.portfolio_identity)
        self.participant_reference = _validate_participant_reference(self.participant_reference)
        self.point_in_time = _validate_point_in_time(self.point_in_time)
        self.positions = _validate_positions(self.positions)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Portfolio):
            return NotImplemented
        return self.portfolio_identity == other.portfolio_identity

    def __hash__(self) -> int:
        return hash(self.portfolio_identity)

    def __str__(self) -> str:
        return (
            f"{self.portfolio_identity} {self.participant_reference} "
            f"{self.point_in_time} positions={len(self.positions)}"
        )

    def __repr__(self) -> str:
        return (
            "Portfolio("
            f"portfolio_identity={self.portfolio_identity!r}, "
            f"participant_reference={self.participant_reference!r}, "
            f"point_in_time={self.point_in_time!r}, "
            f"positions={self.positions!r}"
            ")"
        )
