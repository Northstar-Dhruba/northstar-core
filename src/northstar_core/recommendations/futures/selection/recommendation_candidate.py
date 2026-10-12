"""The outcome of candidate selection for one frozen research decision.

A FuturesRecommendationCandidate is a decision accepted for consideration by
recommendation generation. It is not a recommendation: it has no direction,
entry, stop, target or validity, and it carries its research action -- BUY or
SELL -- unchanged. Mapping a research action to LONG or SHORT is not approved
here (ADR-017); it belongs to recommendation generation. A HOLD decision states
no direction and can never be a candidate.

A FuturesCandidateRejection is a decision that was not selected, with exactly
one CandidateRejectionReason. Selection checks reasons in this fixed priority
and records the first that applies:

1. AFTER_SELECTION_SESSION -- decided after the selection session (look-ahead);
2. STALE_DECISION          -- decided before the selection session (stale or
                              superseded);
3. UNSUPPORTED_TIMEFRAME   -- not on the daily timeframe;
4. UNAPPROVED_PRODUCT      -- the contract's product is not approved;
5. UNAPPROVED_STRATEGY     -- the strategy is not approved;
6. NO_DIRECTIONAL_VIEW     -- the research action is HOLD.

Both keep the whole FuturesResearchDecision, so provenance -- reference,
research action, strategy and analysis -- is never lost.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.futures import FuturesContract
from northstar_core.recommendations.futures.selection.research_decision import (
    FuturesResearchDecision,
)
from northstar_core.recommendations.futures.value_objects import (
    FuturesResearchDecisionReference,
)
from northstar_core.strategy import RecommendationAction, StrategyIdentity

_HOLD = RecommendationAction("HOLD")


class CandidateRejectionReason(StrEnum):
    """Closed vocabulary for why a research decision was not selected, by priority."""

    AFTER_SELECTION_SESSION = "AFTER_SELECTION_SESSION"
    STALE_DECISION = "STALE_DECISION"
    UNSUPPORTED_TIMEFRAME = "UNSUPPORTED_TIMEFRAME"
    UNAPPROVED_PRODUCT = "UNAPPROVED_PRODUCT"
    UNAPPROVED_STRATEGY = "UNAPPROVED_STRATEGY"
    NO_DIRECTIONAL_VIEW = "NO_DIRECTIONAL_VIEW"


class InvalidFuturesRecommendationCandidateError(ValidationError):
    """Raised when a FuturesRecommendationCandidate value is invalid."""


class InvalidFuturesCandidateRejectionError(ValidationError):
    """Raised when a FuturesCandidateRejection value is invalid."""


@dataclass(frozen=True, slots=True)
class FuturesRecommendationCandidate:
    """Immutable frozen research decision accepted for recommendation consideration."""

    decision: FuturesResearchDecision

    def __post_init__(self) -> None:
        if not isinstance(self.decision, FuturesResearchDecision):
            raise InvalidFuturesRecommendationCandidateError(
                "FuturesRecommendationCandidate decision must be a FuturesResearchDecision value."
            )
        if self.decision.research_action == _HOLD:
            raise InvalidFuturesRecommendationCandidateError(
                "A HOLD research decision states no direction and cannot be a candidate."
            )

    @property
    def source(self) -> FuturesResearchDecisionReference:
        """Return the natural key of the frozen research decision."""
        return self.decision.reference

    @property
    def research_action(self) -> RecommendationAction:
        """Return the research action, BUY or SELL, exactly as decided."""
        return self.decision.research_action

    @property
    def contract(self) -> FuturesContract:
        """Return the contract the research decided on."""
        return self.decision.reference.contract

    @property
    def strategy_identity(self) -> StrategyIdentity:
        """Return the strategy that made the decision."""
        return self.decision.reference.strategy_identity

    def __str__(self) -> str:
        return f"candidate {self.decision}"

    def __repr__(self) -> str:
        return f"FuturesRecommendationCandidate(decision={self.decision!r})"


@dataclass(frozen=True, slots=True)
class FuturesCandidateRejection:
    """Immutable frozen research decision not selected, with its single reason."""

    decision: FuturesResearchDecision
    reason: CandidateRejectionReason

    def __post_init__(self) -> None:
        if not isinstance(self.decision, FuturesResearchDecision):
            raise InvalidFuturesCandidateRejectionError(
                "FuturesCandidateRejection decision must be a FuturesResearchDecision value."
            )
        if not isinstance(self.reason, CandidateRejectionReason):
            raise InvalidFuturesCandidateRejectionError(
                "FuturesCandidateRejection reason must be a CandidateRejectionReason value."
            )

    def __str__(self) -> str:
        return f"rejected {self.decision}: {self.reason}"

    def __repr__(self) -> str:
        return f"FuturesCandidateRejection(decision={self.decision!r}, reason={self.reason!r})"
