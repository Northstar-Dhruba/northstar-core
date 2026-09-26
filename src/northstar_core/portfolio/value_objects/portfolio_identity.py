"""Portfolio-specific aggregate identity value object.

PortfolioIdentity preserves the stable opaque identity of one Portfolio
aggregate. It remains independent of positions, participant attribution,
Trades, and Market Data meaning.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidPortfolioIdentityError(ValidationError):
    """Raised when a PortfolioIdentity value is invalid."""


def _normalize(identity: str) -> str:
    if identity is None:
        raise InvalidPortfolioIdentityError("PortfolioIdentity cannot be None.")
    if not isinstance(identity, str):
        raise InvalidPortfolioIdentityError("PortfolioIdentity must be a string.")

    normalized = identity.strip()
    if not normalized:
        raise InvalidPortfolioIdentityError("PortfolioIdentity cannot be empty.")

    return normalized


@dataclass(frozen=True, slots=True)
class PortfolioIdentity:
    """Immutable Portfolio-specific Value Object for opaque aggregate identity.

    PortfolioIdentity has no independent business meaning beyond identifying
    one Portfolio aggregate. Its format is intentionally not defined here.
    """

    identity: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _normalize(self.identity))

    def __str__(self) -> str:
        return self.identity

    def __repr__(self) -> str:
        return f"PortfolioIdentity(identity={self.identity!r})"
