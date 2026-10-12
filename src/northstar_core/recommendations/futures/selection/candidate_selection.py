"""Deterministic selection of recommendation candidates for one session.

``FuturesCandidateSelection.select(criteria, decisions)`` partitions frozen
research decisions into candidates and rejections. It is pure: it reads no
clock, generates no identifier, performs no I/O and mutates nothing.

- Identical decisions supplied more than once are one decision. Two different
  decisions under one reference are contradictory frozen evidence: selection
  refuses them rather than pick one.
- Each distinct decision becomes exactly one candidate or one rejection, using
  the fixed rule priority documented with CandidateRejectionReason.
- The result does not depend on input order. Candidates and rejections are
  each sorted by product, expiration, timeframe, strategy and then decision
  instant, compared chronologically.

Every contract of an approved product may yield a candidate, and each approved
strategy yields its own: selection neither rolls contracts nor arbitrates
between strategies. Building a selection directly from its parts recomputes it
and refuses anything the criteria would not have produced.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cmp_to_key

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Timeframe
from northstar_core.recommendations.futures.selection.candidate_selection_criteria import (
    FuturesCandidateSelectionCriteria,
)
from northstar_core.recommendations.futures.selection.recommendation_candidate import (
    CandidateRejectionReason,
    FuturesCandidateRejection,
    FuturesRecommendationCandidate,
)
from northstar_core.recommendations.futures.selection.research_decision import (
    FuturesResearchDecision,
)
from northstar_core.recommendations.futures.value_objects import (
    FuturesResearchDecisionReference,
)
from northstar_core.strategy import RecommendationAction

# The only timeframe whose candle semantics trade recommendations define (F-2).
_DAILY = Timeframe("1d")
_HOLD = RecommendationAction("HOLD")


class InvalidFuturesCandidateSelectionError(ValidationError):
    """Raised when selection input is contradictory or a stored selection is not genuine."""


def _compare_decisions(first: FuturesResearchDecision, second: FuturesResearchDecision) -> int:
    first_ref, second_ref = first.reference, second.reference
    first_key = (
        first_ref.contract.product,
        first_ref.contract.expiration_date,
        first_ref.timeframe.value,
        first_ref.strategy_identity.identity,
    )
    second_key = (
        second_ref.contract.product,
        second_ref.contract.expiration_date,
        second_ref.timeframe.value,
        second_ref.strategy_identity.identity,
    )
    if first_key != second_key:
        return -1 if first_key < second_key else 1
    return first_ref.decision_instant.compare(second_ref.decision_instant)


_DECISION_ORDER = cmp_to_key(_compare_decisions)


def _distinct(
    decisions: tuple[FuturesResearchDecision, ...],
) -> tuple[FuturesResearchDecision, ...]:
    by_reference: dict[FuturesResearchDecisionReference, FuturesResearchDecision] = {}
    for decision in decisions:
        if not isinstance(decision, FuturesResearchDecision):
            raise InvalidFuturesCandidateSelectionError(
                "FuturesCandidateSelection decisions must be FuturesResearchDecision values."
            )
        known = by_reference.get(decision.reference)
        if known is None:
            by_reference[decision.reference] = decision
        elif known != decision:
            raise InvalidFuturesCandidateSelectionError(
                f"Two different research decisions share the reference {decision.reference}; "
                "frozen evidence is contradictory."
            )
    return tuple(sorted(by_reference.values(), key=_DECISION_ORDER))


def _rejection_reason(
    criteria: FuturesCandidateSelectionCriteria, decision: FuturesResearchDecision
) -> CandidateRejectionReason | None:
    reference = decision.reference
    position = reference.decision_instant.compare(criteria.session_close)
    if position > 0:
        return CandidateRejectionReason.AFTER_SELECTION_SESSION
    if position < 0:
        return CandidateRejectionReason.STALE_DECISION
    if reference.timeframe != _DAILY:
        return CandidateRejectionReason.UNSUPPORTED_TIMEFRAME
    if reference.contract.product not in criteria.products:
        return CandidateRejectionReason.UNAPPROVED_PRODUCT
    if reference.strategy_identity not in criteria.strategies:
        return CandidateRejectionReason.UNAPPROVED_STRATEGY
    if decision.research_action == _HOLD:
        return CandidateRejectionReason.NO_DIRECTIONAL_VIEW
    return None


def _partition(
    criteria: FuturesCandidateSelectionCriteria,
    decisions: tuple[FuturesResearchDecision, ...],
) -> tuple[tuple[FuturesRecommendationCandidate, ...], tuple[FuturesCandidateRejection, ...]]:
    candidates: list[FuturesRecommendationCandidate] = []
    rejections: list[FuturesCandidateRejection] = []
    for decision in decisions:
        reason = _rejection_reason(criteria, decision)
        if reason is None:
            candidates.append(FuturesRecommendationCandidate(decision))
        else:
            rejections.append(FuturesCandidateRejection(decision, reason))
    return tuple(candidates), tuple(rejections)


def _validate_criteria(
    value: FuturesCandidateSelectionCriteria,
) -> FuturesCandidateSelectionCriteria:
    if not isinstance(value, FuturesCandidateSelectionCriteria):
        raise InvalidFuturesCandidateSelectionError(
            "FuturesCandidateSelection criteria must be a FuturesCandidateSelectionCriteria value."
        )
    return value


def _validate_parts(
    candidates: tuple[FuturesRecommendationCandidate, ...],
    rejections: tuple[FuturesCandidateRejection, ...],
) -> None:
    if not isinstance(candidates, tuple) or not all(
        isinstance(candidate, FuturesRecommendationCandidate) for candidate in candidates
    ):
        raise InvalidFuturesCandidateSelectionError(
            "FuturesCandidateSelection candidates must be a tuple of "
            "FuturesRecommendationCandidate values."
        )
    if not isinstance(rejections, tuple) or not all(
        isinstance(rejection, FuturesCandidateRejection) for rejection in rejections
    ):
        raise InvalidFuturesCandidateSelectionError(
            "FuturesCandidateSelection rejections must be a tuple of "
            "FuturesCandidateRejection values."
        )


@dataclass(frozen=True, slots=True)
class FuturesCandidateSelection:
    """Immutable result of selecting candidates: criteria, candidates and rejections."""

    criteria: FuturesCandidateSelectionCriteria
    candidates: tuple[FuturesRecommendationCandidate, ...]
    rejections: tuple[FuturesCandidateRejection, ...]

    def __post_init__(self) -> None:
        criteria = _validate_criteria(self.criteria)
        _validate_parts(self.candidates, self.rejections)
        decisions = tuple(candidate.decision for candidate in self.candidates) + tuple(
            rejection.decision for rejection in self.rejections
        )
        distinct = _distinct(decisions)
        if len(distinct) != len(decisions):
            raise InvalidFuturesCandidateSelectionError(
                "FuturesCandidateSelection lists a research decision more than once."
            )
        if _partition(criteria, distinct) != (self.candidates, self.rejections):
            raise InvalidFuturesCandidateSelectionError(
                "FuturesCandidateSelection is not what its criteria produce from its decisions."
            )

    @classmethod
    def select(
        cls,
        criteria: FuturesCandidateSelectionCriteria,
        decisions: tuple[FuturesResearchDecision, ...],
    ) -> FuturesCandidateSelection:
        """Return the deterministic selection of the given decisions under the criteria."""
        criteria = _validate_criteria(criteria)
        if not isinstance(decisions, tuple):
            raise InvalidFuturesCandidateSelectionError(
                "FuturesCandidateSelection decisions must be a tuple of "
                "FuturesResearchDecision values."
            )
        candidates, rejections = _partition(criteria, _distinct(decisions))
        return cls(criteria=criteria, candidates=candidates, rejections=rejections)

    def __str__(self) -> str:
        return (
            f"{len(self.candidates)} candidate(s), {len(self.rejections)} rejection(s) "
            f"for session {self.criteria.session_close}"
        )

    def __repr__(self) -> str:
        return (
            "FuturesCandidateSelection("
            f"criteria={self.criteria!r}, "
            f"candidates={self.candidates!r}, "
            f"rejections={self.rejections!r}"
            ")"
        )
