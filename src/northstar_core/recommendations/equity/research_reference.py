"""The research candidate an equity recommendation is formed from (EI4-D2, ADR-020).

Core cannot import the Application's EI-3A research decision or EI-3C
timeline, so a candidate is referenced by value: its strategy and research
configuration version, listing, trading date, decision instant and the
fingerprints that identify it.

The fingerprints are checked for shape only -- each must carry its own EI-2B or
EI-3 prefix and a 64-digit lowercase hexadecimal digest -- so a decision
fingerprint can never be passed as an entry fingerprint. Core cannot verify
that the reference names the authoritative first CANDIDATE of a verified
timeline. That is the Application's responsibility (EI4-D2), and a reference
is only as true as the Application that built it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.recommendations.equity.synthetic_inputs import EquitySyntheticVersion
from northstar_core.strategy import StrategyIdentity

_HEX = frozenset("0123456789abcdef")
_PREFIXES = {
    "research_decision_fingerprint": "eir1-sha256:",
    "candidate_entry_fingerprint": "eirt1-sha256:",
    "evidence_snapshot_id": "ecs1-sha256:",
}


class InvalidEquityResearchCandidateReferenceError(ValidationError):
    """Raised when an EquityResearchCandidateReference is invalid."""


def _check_digest(value: object, field_name: str) -> None:
    prefix = _PREFIXES[field_name]
    if not isinstance(value, str) or not value.startswith(prefix):
        raise InvalidEquityResearchCandidateReferenceError(
            f"EquityResearchCandidateReference {field_name} must begin {prefix!r}."
        )
    digest = value[len(prefix) :]
    if len(digest) != 64 or not set(digest) <= _HEX:
        raise InvalidEquityResearchCandidateReferenceError(
            f"EquityResearchCandidateReference {field_name} must end in a 64-digit hex digest."
        )


@dataclass(frozen=True, slots=True)
class EquityResearchCandidateReference:
    """An immutable reference to one EI-3 research candidate, as the Application asserts it."""

    strategy: StrategyIdentity
    research_configuration_version: EquitySyntheticVersion
    listing: ListingReference
    trading_date: date
    decision_as_of: PointInTime
    research_decision_fingerprint: str
    candidate_entry_fingerprint: str
    evidence_snapshot_id: str

    def __post_init__(self) -> None:
        error = InvalidEquityResearchCandidateReferenceError
        if not isinstance(self.strategy, StrategyIdentity):
            raise error("EquityResearchCandidateReference strategy must be a StrategyIdentity.")
        if not isinstance(self.research_configuration_version, EquitySyntheticVersion):
            raise error(
                "EquityResearchCandidateReference research configuration version must be an "
                "EquitySyntheticVersion: EI-3 research calibration is synthetic."
            )
        if not isinstance(self.listing, ListingReference):
            raise error("EquityResearchCandidateReference listing must be a ListingReference.")
        if type(self.trading_date) is not date:
            raise error("EquityResearchCandidateReference trading date must be a plain date.")
        if not isinstance(self.decision_as_of, PointInTime):
            raise error("EquityResearchCandidateReference decision_as_of must be a PointInTime.")
        for field_name in _PREFIXES:
            _check_digest(getattr(self, field_name), field_name)

    def document(self) -> dict[str, Any]:
        """Return the canonical content."""
        return {
            "strategy": self.strategy.identity,
            "research_configuration_version": self.research_configuration_version.value,
            "listing": {
                "symbol": self.listing.symbol.value,
                "exchange_code": self.listing.exchange_code.value,
            },
            "trading_date": self.trading_date.isoformat(),
            "decision_as_of": self.decision_as_of.value,
            "research_decision_fingerprint": self.research_decision_fingerprint,
            "candidate_entry_fingerprint": self.candidate_entry_fingerprint,
            "evidence_snapshot_id": self.evidence_snapshot_id,
        }
