"""Portfolio-owned Listing-specific ownership interpretation entity.

Position is a mutable subordinate entity owned by Portfolio. It composes only
Listing; participant and temporal context are inherited from its Portfolio.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.domain.listing import Listing
from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidPositionError(ValidationError):
    """Raised when a Position entity is invalid."""


def _validate_listing(value: Listing) -> Listing:
    if value is None:
        raise InvalidPositionError("Position listing cannot be None.")
    if not isinstance(value, Listing):
        raise InvalidPositionError("Position listing must be a Listing entity.")
    return value


@dataclass(slots=True, eq=False)
class Position:
    """Portfolio-owned entity for Listing-specific ownership interpretation.

    Position is mutable because Portfolio ownership interpretation evolves over
    time. Position identity remains local to its owning Portfolio and Listing;
    equality is intentionally unresolved in Version 1.0.
    """

    listing: Listing

    def __post_init__(self) -> None:
        self.listing = _validate_listing(self.listing)

    def __repr__(self) -> str:
        return f"Position(listing={self.listing!r})"
