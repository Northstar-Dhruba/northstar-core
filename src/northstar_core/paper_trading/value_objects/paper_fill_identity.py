"""Paper fill-specific identity value object.

PaperFillIdentity preserves the stable opaque identity of one paper fill. It remains
independent of order, listing, quantity, price, and temporal meaning.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidPaperFillIdentityError(ValidationError):
    """Raised when a PaperFillIdentity value is invalid."""


def _normalize(identity: str) -> str:
    if identity is None:
        raise InvalidPaperFillIdentityError("PaperFillIdentity cannot be None.")
    if not isinstance(identity, str):
        raise InvalidPaperFillIdentityError("PaperFillIdentity must be a string.")

    normalized = identity.strip()
    if not normalized:
        raise InvalidPaperFillIdentityError("PaperFillIdentity cannot be empty.")

    return normalized


@dataclass(frozen=True, slots=True)
class PaperFillIdentity:
    """Immutable paper-trading Value Object for opaque paper fill identity.

    PaperFillIdentity has no independent business meaning beyond identifying one
    paper fill. Its format is intentionally not defined here.
    """

    identity: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _normalize(self.identity))

    def __str__(self) -> str:
        return self.identity

    def __repr__(self) -> str:
        return f"PaperFillIdentity(identity={self.identity!r})"
