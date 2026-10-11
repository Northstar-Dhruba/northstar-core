"""Evidence that a recommendation's validity has passed, without a further bar.

A recommendation normally expires on a completed bar at or after
``valid_through``. After a contract's last session no later bar can exist, and
the final bar itself may be missing or stamped at another instant, so expiry
must also be possible from time alone. That expiry has to state what is known
about the observations it did not see.

TimeExpiryEvidence is that statement, supplied by the caller:

- ``as_of`` is the instant the expiry is evaluated at; it reads no clock.
- ``evaluated_through`` is the completion instant of the last bar the
  lifecycle evaluated, or None if it evaluated none. It must match the
  lifecycle it is applied to, which ties the claim to the evaluated history.
- ``coverage`` says whether every eligible observation through the validity
  window was present, approved and evaluated in order:

  - COMPLETE_VERIFIED_COVERAGE is a positive assertion that it was. It names
    no deficiency, and requires that at least one bar was evaluated.
  - INCOMPLETE_OR_UNVERIFIED_COVERAGE says some required observation is
    missing, unapproved or unverified, and names which with a deficiency.

- ``attested_by`` is opaque text naming who made the coverage assessment, so
  its provenance and the responsibility for it stay visible.

Core cannot verify a data provider, an approval manifest or an exchange
calendar, so it never manufactures COMPLETE_VERIFIED_COVERAGE: the assertion is
a trusted caller statement, not proof. Only a trusted Application service that
has checked coverage against the trading-session calendar and the approved
stored bars may supply it. Nothing here is provider-specific.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime


class ObservationCoverage(StrEnum):
    """Whether the observations behind a time-driven expiry are known complete."""

    COMPLETE_VERIFIED_COVERAGE = "COMPLETE_VERIFIED_COVERAGE"
    INCOMPLETE_OR_UNVERIFIED_COVERAGE = "INCOMPLETE_OR_UNVERIFIED_COVERAGE"


class CoverageDeficiency(StrEnum):
    """Why the observations behind a time-driven expiry are not known complete."""

    MISSING_OBSERVATIONS = "MISSING_OBSERVATIONS"
    UNAPPROVED_OBSERVATIONS = "UNAPPROVED_OBSERVATIONS"
    UNVERIFIED_OBSERVATIONS = "UNVERIFIED_OBSERVATIONS"


class InvalidTimeExpiryEvidenceError(ValidationError):
    """Raised when a TimeExpiryEvidence value is invalid."""


def _validate_as_of(value: PointInTime) -> PointInTime:
    if not isinstance(value, PointInTime):
        raise InvalidTimeExpiryEvidenceError(
            "TimeExpiryEvidence as of must be a PointInTime value."
        )
    return value


def _validate_evaluated_through(value: PointInTime | None) -> PointInTime | None:
    if value is not None and not isinstance(value, PointInTime):
        raise InvalidTimeExpiryEvidenceError(
            "TimeExpiryEvidence evaluated through must be a PointInTime value or None."
        )
    return value


def _validate_coverage(value: ObservationCoverage) -> ObservationCoverage:
    if not isinstance(value, ObservationCoverage):
        raise InvalidTimeExpiryEvidenceError(
            "TimeExpiryEvidence coverage must be an ObservationCoverage value."
        )
    return value


def _normalize_attested_by(value: str) -> str:
    if not isinstance(value, str):
        raise InvalidTimeExpiryEvidenceError("TimeExpiryEvidence attested by must be a string.")
    normalized = value.strip()
    if not normalized:
        raise InvalidTimeExpiryEvidenceError("TimeExpiryEvidence attested by cannot be empty.")
    return normalized


def _validate_deficiency(
    coverage: ObservationCoverage, value: CoverageDeficiency | None
) -> CoverageDeficiency | None:
    if coverage is ObservationCoverage.COMPLETE_VERIFIED_COVERAGE:
        if value is not None:
            raise InvalidTimeExpiryEvidenceError(
                "TimeExpiryEvidence with complete verified coverage cannot name a deficiency."
            )
    elif not isinstance(value, CoverageDeficiency):
        raise InvalidTimeExpiryEvidenceError(
            "TimeExpiryEvidence with incomplete or unverified coverage must name a "
            "CoverageDeficiency."
        )
    return value


@dataclass(frozen=True, slots=True)
class TimeExpiryEvidence:
    """Immutable caller-supplied evidence for expiring a recommendation by time.

    Invariants:
        - ``evaluated_through`` is not later than ``as_of``.
        - Complete verified coverage names no deficiency and requires
          ``evaluated_through``.
        - Incomplete or unverified coverage names exactly one deficiency.
        - ``attested_by`` is non-empty.
    """

    as_of: PointInTime
    evaluated_through: PointInTime | None
    coverage: ObservationCoverage
    attested_by: str
    deficiency: CoverageDeficiency | None = None

    def __post_init__(self) -> None:
        as_of = _validate_as_of(self.as_of)
        evaluated_through = _validate_evaluated_through(self.evaluated_through)
        coverage = _validate_coverage(self.coverage)
        attested_by = _normalize_attested_by(self.attested_by)
        deficiency = _validate_deficiency(coverage, self.deficiency)

        if evaluated_through is not None and evaluated_through.compare(as_of) > 0:
            raise InvalidTimeExpiryEvidenceError(
                "TimeExpiryEvidence evaluated through cannot be later than as of."
            )
        if coverage is ObservationCoverage.COMPLETE_VERIFIED_COVERAGE and evaluated_through is None:
            raise InvalidTimeExpiryEvidenceError(
                "TimeExpiryEvidence cannot assert complete verified coverage with no "
                "evaluated observation."
            )

        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "evaluated_through", evaluated_through)
        object.__setattr__(self, "coverage", coverage)
        object.__setattr__(self, "attested_by", attested_by)
        object.__setattr__(self, "deficiency", deficiency)

    @property
    def is_verified(self) -> bool:
        """Return whether the caller asserted complete verified coverage."""
        return self.coverage is ObservationCoverage.COMPLETE_VERIFIED_COVERAGE

    def __str__(self) -> str:
        deficiency = f" ({self.deficiency})" if self.deficiency is not None else ""
        return f"{self.coverage}{deficiency} as of {self.as_of} attested by {self.attested_by}"

    def __repr__(self) -> str:
        return (
            "TimeExpiryEvidence("
            f"as_of={self.as_of!r}, "
            f"evaluated_through={self.evaluated_through!r}, "
            f"coverage={self.coverage!r}, "
            f"attested_by={self.attested_by!r}, "
            f"deficiency={self.deficiency!r}"
            ")"
        )
