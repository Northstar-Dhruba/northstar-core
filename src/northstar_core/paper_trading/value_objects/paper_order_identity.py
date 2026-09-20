"""Paper order-specific identity value object.

PaperOrderIdentity preserves the stable opaque identity of one paper order. It remains
independent of listing, strategy, side, quantity, and result meaning.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidPaperOrderIdentityError(ValidationError):
    """Raised when a PaperOrderIdentity value is invalid."""


def _normalize(identity: str) -> str:
    if identity is None:
        raise InvalidPaperOrderIdentityError("PaperOrderIdentity cannot be None.")
    if not isinstance(identity, str):
        raise InvalidPaperOrderIdentityError("PaperOrderIdentity must be a string.")

    normalized = identity.strip()
    if not normalized:
        raise InvalidPaperOrderIdentityError("PaperOrderIdentity cannot be empty.")

    return normalized


@dataclass(frozen=True, slots=True)
class PaperOrderIdentity:
    """Immutable paper-trading Value Object for opaque paper order identity.

    PaperOrderIdentity has no independent business meaning beyond identifying one
    paper order. Its format is intentionally not defined here.
    """

    identity: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _normalize(self.identity))

    def __str__(self) -> str:
        return self.identity

    def __repr__(self) -> str:
        return f"PaperOrderIdentity(identity={self.identity!r})"
