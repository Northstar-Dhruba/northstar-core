"""The frozen market evidence one candidate's levels are generated from.

The evidence pairs a candidate's decision reference with the frozen
FuturesMarketObservationContext the research decided on. It is the only market
input generation reads: F-4 fetches no bars and builds no replacement evidence.

The two must describe the same decision, so a mismatch is an invalid input and
raises; it is never a rejection:

- the same contract;
- the same instant, so nothing later than the decision -- no look-ahead -- and
  nothing older can be used;
- the daily timeframe on both;
- the last recent close is the latest quote, so the evidence ends at its own
  decision-session close, which is the reference price.

The context carries no strategy; the strategy is represented on the reference.
Core cannot verify that the evidence is the stored frozen record, or that the
history it holds is complete, approved and final; the Application supplies it.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Timeframe
from northstar_core.recommendations.futures.value_objects import (
    FuturesResearchDecisionReference,
)
from northstar_core.strategy import FuturesMarketObservationContext

_DAILY = Timeframe("1d")


class InvalidFuturesCandidateEvidenceError(ValidationError):
    """Raised when a FuturesCandidateEvidence value is invalid."""


def _validate_agreement(
    source: FuturesResearchDecisionReference, context: FuturesMarketObservationContext
) -> None:
    if context.contract != source.contract:
        raise InvalidFuturesCandidateEvidenceError(
            f"FuturesCandidateEvidence context contract {context.contract} does not match "
            f"the decision contract {source.contract}."
        )
    if context.observed_at.compare(source.decision_instant) != 0:
        raise InvalidFuturesCandidateEvidenceError(
            f"FuturesCandidateEvidence context instant {context.observed_at} does not match "
            f"the decision instant {source.decision_instant}."
        )
    if source.timeframe != _DAILY or context.timeframe != _DAILY:
        raise InvalidFuturesCandidateEvidenceError(
            "FuturesCandidateEvidence decision and context must both be on the 1d timeframe."
        )
    if context.recent_closes[-1] != context.latest_quote:
        raise InvalidFuturesCandidateEvidenceError(
            "FuturesCandidateEvidence recent closes must end at the decision close."
        )


@dataclass(frozen=True, slots=True)
class FuturesCandidateEvidence:
    """Immutable frozen market evidence for one candidate's research decision."""

    source: FuturesResearchDecisionReference
    context: FuturesMarketObservationContext

    def __post_init__(self) -> None:
        if not isinstance(self.source, FuturesResearchDecisionReference):
            raise InvalidFuturesCandidateEvidenceError(
                "FuturesCandidateEvidence source must be a FuturesResearchDecisionReference value."
            )
        if not isinstance(self.context, FuturesMarketObservationContext):
            raise InvalidFuturesCandidateEvidenceError(
                "FuturesCandidateEvidence context must be a FuturesMarketObservationContext value."
            )
        _validate_agreement(self.source, self.context)

    def __str__(self) -> str:
        return f"evidence for {self.source}"

    def __repr__(self) -> str:
        return f"FuturesCandidateEvidence(source={self.source!r}, context={self.context!r})"
