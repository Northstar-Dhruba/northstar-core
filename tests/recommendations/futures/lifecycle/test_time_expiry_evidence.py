"""Tests for the caller-supplied evidence behind a time-driven expiry."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.recommendations.futures import (
    CoverageDeficiency,
    InvalidTimeExpiryEvidenceError,
    ObservationCoverage,
    TimeExpiryEvidence,
)

_AS_OF = PointInTime("2026-10-28T00:00:00Z")
_THROUGH = PointInTime("2026-10-26T10:00:00Z")
_VERIFIED = ObservationCoverage.COMPLETE_VERIFIED_COVERAGE
_INCOMPLETE = ObservationCoverage.INCOMPLETE_OR_UNVERIFIED_COVERAGE


def _evidence(**overrides: object) -> TimeExpiryEvidence:
    fields: dict[str, object] = {
        "as_of": _AS_OF,
        "evaluated_through": _THROUGH,
        "coverage": _INCOMPLETE,
        "attested_by": "synthetic-coverage-check",
        "deficiency": CoverageDeficiency.MISSING_OBSERVATIONS,
    }
    fields.update(overrides)
    return TimeExpiryEvidence(**fields)  # type: ignore[arg-type]


def test_the_coverage_vocabularies_are_closed() -> None:
    assert [coverage.value for coverage in ObservationCoverage] == [
        "COMPLETE_VERIFIED_COVERAGE",
        "INCOMPLETE_OR_UNVERIFIED_COVERAGE",
    ]
    assert [deficiency.value for deficiency in CoverageDeficiency] == [
        "MISSING_OBSERVATIONS",
        "UNAPPROVED_OBSERVATIONS",
        "UNVERIFIED_OBSERVATIONS",
    ]


@pytest.mark.parametrize("deficiency", list(CoverageDeficiency))
def test_incomplete_coverage_names_its_deficiency(deficiency: CoverageDeficiency) -> None:
    evidence = _evidence(deficiency=deficiency)

    assert evidence.deficiency is deficiency
    assert not evidence.is_verified


def test_incomplete_coverage_without_a_deficiency_is_rejected() -> None:
    with pytest.raises(InvalidTimeExpiryEvidenceError, match="must name a CoverageDeficiency"):
        _evidence(deficiency=None)


def test_incomplete_coverage_may_follow_no_evaluated_observation() -> None:
    assert _evidence(evaluated_through=None).evaluated_through is None


def test_verified_coverage_names_no_deficiency() -> None:
    evidence = _evidence(coverage=_VERIFIED, deficiency=None)

    assert evidence.is_verified
    assert evidence.deficiency is None


def test_verified_coverage_with_a_deficiency_is_rejected() -> None:
    with pytest.raises(InvalidTimeExpiryEvidenceError, match="cannot name a deficiency"):
        _evidence(coverage=_VERIFIED, deficiency=CoverageDeficiency.MISSING_OBSERVATIONS)


def test_verified_coverage_requires_an_evaluated_observation() -> None:
    """Coverage of nothing cannot be complete: Core never manufactures verification."""
    with pytest.raises(InvalidTimeExpiryEvidenceError, match="no evaluated observation"):
        _evidence(coverage=_VERIFIED, deficiency=None, evaluated_through=None)


def test_evaluated_through_cannot_be_later_than_as_of() -> None:
    with pytest.raises(InvalidTimeExpiryEvidenceError, match="cannot be later than as of"):
        _evidence(evaluated_through=PointInTime("2026-10-28T00:00:00.000001Z"))


def test_evaluated_through_may_equal_as_of() -> None:
    assert _evidence(evaluated_through=_AS_OF).evaluated_through == _AS_OF


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("as_of", None, "as of must be a PointInTime"),
        ("as_of", "2026-10-28T00:00:00Z", "as of must be a PointInTime"),
        ("evaluated_through", "2026-10-26T10:00:00Z", "evaluated through must be"),
        ("coverage", "COMPLETE_VERIFIED_COVERAGE", "ObservationCoverage"),
        ("coverage", None, "ObservationCoverage"),
        ("deficiency", "MISSING_OBSERVATIONS", "CoverageDeficiency"),
        ("attested_by", None, "attested by must be a string"),
        ("attested_by", 7, "attested by must be a string"),
        ("attested_by", "   ", "attested by cannot be empty"),
    ],
)
def test_fields_require_their_domain_types(field: str, value: object, message: str) -> None:
    with pytest.raises(InvalidTimeExpiryEvidenceError, match=message):
        _evidence(**{field: value})


def test_attested_by_is_stripped() -> None:
    assert _evidence(attested_by="  application:coverage-v1  ").attested_by == (
        "application:coverage-v1"
    )


def test_evidence_is_immutable_comparable_and_hashable() -> None:
    evidence = _evidence()

    assert evidence == _evidence()
    assert hash(evidence) == hash(_evidence())
    assert evidence != _evidence(deficiency=CoverageDeficiency.UNAPPROVED_OBSERVATIONS)
    with pytest.raises(FrozenInstanceError):
        evidence.coverage = _VERIFIED  # type: ignore[misc]


def test_evidence_text_names_coverage_and_provenance() -> None:
    assert str(_evidence()) == (
        "INCOMPLETE_OR_UNVERIFIED_COVERAGE (MISSING_OBSERVATIONS) as of "
        "2026-10-28T00:00:00Z attested by synthetic-coverage-check"
    )
    assert repr(_evidence()).startswith("TimeExpiryEvidence(as_of=")


def test_the_error_is_a_validation_error() -> None:
    assert issubclass(InvalidTimeExpiryEvidenceError, ValidationError)
