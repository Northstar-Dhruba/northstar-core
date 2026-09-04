"""Trade-specific aggregate identity value object.

TradeIdentity preserves the stable opaque identity of one Trade aggregate. It
remains independent of participant, Listing, transaction, execution, and
Market Data meaning.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidTradeIdentityError(ValidationError):
    """Raised when a TradeIdentity value is invalid."""


def _normalize(identity: str) -> str:
    if identity is None:
        raise InvalidTradeIdentityError("TradeIdentity cannot be None.")
    if not isinstance(identity, str):
        raise InvalidTradeIdentityError("TradeIdentity must be a string.")

    normalized = identity.strip()
    if not normalized:
        raise InvalidTradeIdentityError("TradeIdentity cannot be empty.")

    return normalized


@dataclass(frozen=True, slots=True)
class TradeIdentity:
    """Immutable Trades-specific Value Object for opaque aggregate identity.

    TradeIdentity has no independent business meaning beyond identifying one
    Trade aggregate. Its format is intentionally not defined here.
    """

    identity: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _normalize(self.identity))

    def __str__(self) -> str:
        return self.identity

    def __repr__(self) -> str:
        return f"TradeIdentity(identity={self.identity!r})"
