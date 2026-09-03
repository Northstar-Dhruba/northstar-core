"""Participant identity association value object.

ParticipantReference preserves participant attribution by composing one
ParticipantIdentity. It does not own Participant or Participant lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.domain.value_objects.participant_identity import ParticipantIdentity
from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidParticipantReferenceError(ValidationError):
    """Raised when a ParticipantReference value is invalid."""


def _validate_participant_identity(value: ParticipantIdentity) -> ParticipantIdentity:
    if value is None:
        raise InvalidParticipantReferenceError(
            "ParticipantReference participant identity cannot be None."
        )
    if not isinstance(value, ParticipantIdentity):
        raise InvalidParticipantReferenceError(
            "ParticipantReference participant identity must be a ParticipantIdentity value."
        )
    return value


@dataclass(frozen=True, slots=True)
class ParticipantReference:
    """Immutable Core Domain Value Object for participant identity association.

    ParticipantReference identifies one Participant through its
    ParticipantIdentity. It has no independent identity and does not own
    Participant meaning or lifecycle.
    """

    participant_identity: ParticipantIdentity

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "participant_identity",
            _validate_participant_identity(self.participant_identity),
        )

    def __str__(self) -> str:
        return str(self.participant_identity)

    def __repr__(self) -> str:
        return f"ParticipantReference(participant_identity={self.participant_identity!r})"
