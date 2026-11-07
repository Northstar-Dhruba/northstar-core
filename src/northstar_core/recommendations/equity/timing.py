"""The instants of an equity recommendation (EI4-D1, ADR-020).

Three instants are distinct:

- ``decision_as_of``: the EI-3 research decision instant, the evidence
  snapshot's ``as_of`` (EI3-D1);
- the issuance instant: for an ACTUAL issuance, when a real operational
  recommendation was actually issued; for a MODELED issuance, an explicitly
  labelled modeled instant in historical synthetic analysis;
- ``eligible_from``: the earliest modeled or operational entry-eligibility
  instant.

They must not run backwards: ``decision_as_of <= issued_at <= eligible_from``.
An ACTUAL issuance is never backdated, because it is the instant supplied for
it, never derived from ``decision_as_of``. Core reads no clock: every instant
is supplied.

This value states only the instants and their order. Which bars may evidence
an entry -- only bars that open at or after ``eligible_from`` -- and how
``eligible_from`` is resolved from a session grid are Application concerns
(EI-4C). No cutoff time is defined here (EI0-D7).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime


class InvalidEquityRecommendationTimingError(ValidationError):
    """Raised when an EquityRecommendationTiming is invalid."""


class EquityIssuanceKind(StrEnum):
    """Whether an issuance instant is an actual issuance or an explicitly modeled one."""

    ACTUAL = "ACTUAL"
    MODELED = "MODELED"


@dataclass(frozen=True, slots=True)
class EquityRecommendationTiming:
    """The decision, issuance and entry-eligibility instants, in order."""

    decision_as_of: PointInTime
    issuance_kind: EquityIssuanceKind
    issued_at: PointInTime
    eligible_from: PointInTime

    def __post_init__(self) -> None:
        error = InvalidEquityRecommendationTimingError
        for name in ("decision_as_of", "issued_at", "eligible_from"):
            if not isinstance(getattr(self, name), PointInTime):
                raise error(f"EquityRecommendationTiming {name} must be a PointInTime.")
        if not isinstance(self.issuance_kind, EquityIssuanceKind):
            raise error("EquityRecommendationTiming issuance kind must be an EquityIssuanceKind.")
        if self.issued_at.compare(self.decision_as_of) < 0:
            raise error("A recommendation cannot be issued before its research decision.")
        if self.eligible_from.compare(self.issued_at) < 0:
            raise error("Entry eligibility cannot begin before issuance.")

    @property
    def is_actual_issuance(self) -> bool:
        """Return whether ``issued_at`` is an actual, operational issuance."""
        return self.issuance_kind is EquityIssuanceKind.ACTUAL

    def document(self) -> dict[str, Any]:
        """Return the canonical content."""
        return {
            "decision_as_of": self.decision_as_of.value,
            "issuance_kind": self.issuance_kind.value,
            "issued_at": self.issued_at.value,
            "eligible_from": self.eligible_from.value,
        }
