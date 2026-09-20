"""Paper portfolio-specific identity value object.

PaperPortfolioIdentity preserves the stable opaque identity of one paper portfolio. It remains
independent of position content, valuation, and Market Data meaning.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidPaperPortfolioIdentityError(ValidationError):
    """Raised when a PaperPortfolioIdentity value is invalid."""


def _normalize(identity: str) -> str:
    if identity is None:
        raise InvalidPaperPortfolioIdentityError("PaperPortfolioIdentity cannot be None.")
    if not isinstance(identity, str):
        raise InvalidPaperPortfolioIdentityError("PaperPortfolioIdentity must be a string.")

    normalized = identity.strip()
    if not normalized:
        raise InvalidPaperPortfolioIdentityError("PaperPortfolioIdentity cannot be empty.")

    return normalized


@dataclass(frozen=True, slots=True)
class PaperPortfolioIdentity:
    """Immutable paper-trading Value Object for opaque paper portfolio identity.

    PaperPortfolioIdentity has no independent business meaning beyond identifying one
    paper portfolio. Its format is intentionally not defined here.
    """

    identity: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _normalize(self.identity))

    def __str__(self) -> str:
        return self.identity

    def __repr__(self) -> str:
        return f"PaperPortfolioIdentity(identity={self.identity!r})"
