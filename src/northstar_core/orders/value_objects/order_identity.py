"""Order-specific aggregate identity value object.

OrderIdentity preserves the stable opaque identity of one Order aggregate. It
remains independent of participant, Listing, transaction, lifecycle, and
Market Data meaning.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidOrderIdentityError(ValidationError):
    """Raised when an OrderIdentity value is invalid."""


def _normalize(identity: str) -> str:
    if identity is None:
        raise InvalidOrderIdentityError("OrderIdentity cannot be None.")
    if not isinstance(identity, str):
        raise InvalidOrderIdentityError("OrderIdentity must be a string.")

    normalized = identity.strip()
    if not normalized:
        raise InvalidOrderIdentityError("OrderIdentity cannot be empty.")

    return normalized


@dataclass(frozen=True, slots=True)
class OrderIdentity:
    """Immutable Orders-specific Value Object for opaque aggregate identity.

    OrderIdentity has no independent business meaning beyond identifying one
    Order aggregate. Its format is intentionally not defined here.
    """

    identity: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _normalize(self.identity))

    def __str__(self) -> str:
        return self.identity

    def __repr__(self) -> str:
        return f"OrderIdentity(identity={self.identity!r})"
