"""Participant-specific identity value object.

ParticipantIdentity preserves the stable opaque identity of one Participant.
It remains independent of participant profile, lifecycle, Orders, and Market
Data meaning.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidParticipantIdentityError(ValidationError):
    """Raised when a ParticipantIdentity value is invalid."""


def _normalize(identity: str) -> str:
    if identity is None:
        raise InvalidParticipantIdentityError("ParticipantIdentity cannot be None.")
    if not isinstance(identity, str):
        raise InvalidParticipantIdentityError("ParticipantIdentity must be a string.")

    normalized = identity.strip()
    if not normalized:
        raise InvalidParticipantIdentityError("ParticipantIdentity cannot be empty.")

    return normalized


@dataclass(frozen=True, slots=True)
class ParticipantIdentity:
    """Immutable Core Domain Value Object for opaque participant identity.

    ParticipantIdentity has no independent business meaning beyond identifying
    one Participant. Its format is intentionally not defined here.
    """

    identity: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _normalize(self.identity))

    def __str__(self) -> str:
        return self.identity

    def __repr__(self) -> str:
        return f"ParticipantIdentity(identity={self.identity!r})"
