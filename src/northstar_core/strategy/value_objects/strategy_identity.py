"""Strategy-specific aggregate identity value object.

StrategyIdentity preserves the stable opaque identity of one Strategy
aggregate. It remains independent of decision policy, participant attribution,
Orders, Trades, Portfolio, and Market Data meaning.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidStrategyIdentityError(ValidationError):
    """Raised when a StrategyIdentity value is invalid."""


def _normalize(identity: str) -> str:
    if identity is None:
        raise InvalidStrategyIdentityError("StrategyIdentity cannot be None.")
    if not isinstance(identity, str):
        raise InvalidStrategyIdentityError("StrategyIdentity must be a string.")

    normalized = identity.strip()
    if not normalized:
        raise InvalidStrategyIdentityError("StrategyIdentity cannot be empty.")

    return normalized


@dataclass(frozen=True, slots=True)
class StrategyIdentity:
    """Immutable Strategy-specific Value Object for opaque aggregate identity.

    StrategyIdentity has no independent business meaning beyond identifying one
    Strategy aggregate. Its format is intentionally not defined here.
    """

    identity: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _normalize(self.identity))

    def __str__(self) -> str:
        return self.identity

    def __repr__(self) -> str:
        return f"StrategyIdentity(identity={self.identity!r})"
