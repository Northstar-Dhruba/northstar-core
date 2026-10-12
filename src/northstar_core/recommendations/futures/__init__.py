"""Futures trade recommendation bounded context package.

A FuturesTradeRecommendation is an actionable trade setup on one futures
contract: a LONG or SHORT direction, an inclusive entry zone, a fixed stop, a
single target and a validity window -- from the first eligible observation
after issuance through a last observation bounded by the contract cutoff, all
caller-resolved. It references the frozen research decision it came from and the
versioned policy that produced it, and carries a thesis of explanation reasons.

Its lifecycle -- waiting for entry, active, closed at target or stop, expired,
indeterminate on an ambiguous entry observation, or expired by time with
incomplete observation coverage -- is derived from immutable events by the pure
FuturesTradeRecommendationLifecycle transitions: advance over completed bars,
and expire on caller-supplied time evidence. Lifecycle events are observations
and documented modeling rules, never orders, fills, positions or broker
executions.

Research action (BUY, SELL, HOLD), target exposure, trade direction (LONG,
SHORT) and order side are distinct concepts. This package defines only trade
direction and implements no mapping from research actions. It may build on
Foundation, Derivatives, Futures and Strategy; Strategy never imports it, and it
never imports Paper Trading or Broker Execution (ADR-017).

Candidate selection (the ``selection`` sub-package) decides which frozen
research decisions of one final session may be considered for a recommendation:
BUY and SELL decisions of approved products and strategies, with their research
action kept unchanged. A candidate is not a recommendation and has no direction.

Recommendation generation (the ``generation`` sub-package) turns the candidates
of one selection into validated trade-setup proposals under a versioned policy
(ADR-018): BUY maps to LONG and SELL to SHORT, the nearest validity-eligible
contract of each product is selected, and entry, stop and target are derived
from the mean absolute close-to-close change and aligned to a caller-supplied
price increment, subject to a worst-entry reward-to-risk minimum. A proposal has
no identity; ``to_recommendation`` takes a caller-supplied one.

This package models no sizing, margin, persistence, publication, notification,
returns or profit and loss, and generates no identifier.
"""

from .generation import (
    FuturesCandidateEvidence,
    FuturesGenerationRejection,
    FuturesRecommendationGeneration,
    FuturesRecommendationGenerationPolicy,
    FuturesRecommendationProposal,
    FuturesRecommendationSessionWindow,
    GenerationRejectionReason,
    InvalidFuturesCandidateEvidenceError,
    InvalidFuturesGenerationRejectionError,
    InvalidFuturesRecommendationGenerationError,
    InvalidFuturesRecommendationGenerationPolicyError,
    InvalidFuturesRecommendationProposalError,
    InvalidFuturesRecommendationSessionWindowError,
    InvalidPriceMovementUnitError,
    InvalidRewardToRiskError,
    PriceMovementUnit,
    RewardToRisk,
)
from .lifecycle import (
    CoverageDeficiency,
    FuturesTradeRecommendationEvent,
    FuturesTradeRecommendationLifecycle,
    IntrabarOrdering,
    InvalidFuturesTradeRecommendationEventError,
    InvalidFuturesTradeRecommendationExpiryError,
    InvalidFuturesTradeRecommendationLifecycleError,
    InvalidFuturesTradeRecommendationObservationError,
    InvalidTimeExpiryEvidenceError,
    ObservationCoverage,
    RecommendationBoundary,
    RecommendationEventKind,
    RecommendationExpiryReason,
    RecommendationStatus,
    TimeExpiryEvidence,
)
from .selection import (
    CandidateRejectionReason,
    FuturesCandidateRejection,
    FuturesCandidateSelection,
    FuturesCandidateSelectionCriteria,
    FuturesRecommendationCandidate,
    FuturesResearchDecision,
    InvalidFuturesCandidateRejectionError,
    InvalidFuturesCandidateSelectionCriteriaError,
    InvalidFuturesCandidateSelectionError,
    InvalidFuturesRecommendationCandidateError,
    InvalidFuturesResearchDecisionError,
)
from .value_objects import (
    EntryZone,
    FuturesResearchDecisionReference,
    FuturesTradeRecommendation,
    FuturesTradeRecommendationIdentity,
    InvalidEntryZoneError,
    InvalidFuturesResearchDecisionReferenceError,
    InvalidFuturesTradeRecommendationError,
    InvalidFuturesTradeRecommendationIdentityError,
    InvalidPriceTargetError,
    InvalidRecommendationPolicyVersionError,
    InvalidRecommendationValidityError,
    InvalidStopLossError,
    PriceTarget,
    RecommendationPolicyVersion,
    RecommendationValidity,
    StopLoss,
    TradeDirection,
)

__all__ = [
    "CandidateRejectionReason",
    "CoverageDeficiency",
    "EntryZone",
    "FuturesCandidateEvidence",
    "FuturesCandidateRejection",
    "FuturesCandidateSelection",
    "FuturesCandidateSelectionCriteria",
    "FuturesGenerationRejection",
    "FuturesRecommendationCandidate",
    "FuturesRecommendationGeneration",
    "FuturesRecommendationGenerationPolicy",
    "FuturesRecommendationProposal",
    "FuturesRecommendationSessionWindow",
    "FuturesResearchDecision",
    "FuturesResearchDecisionReference",
    "FuturesTradeRecommendation",
    "FuturesTradeRecommendationEvent",
    "FuturesTradeRecommendationIdentity",
    "FuturesTradeRecommendationLifecycle",
    "GenerationRejectionReason",
    "IntrabarOrdering",
    "InvalidEntryZoneError",
    "InvalidFuturesCandidateEvidenceError",
    "InvalidFuturesCandidateRejectionError",
    "InvalidFuturesCandidateSelectionCriteriaError",
    "InvalidFuturesCandidateSelectionError",
    "InvalidFuturesGenerationRejectionError",
    "InvalidFuturesRecommendationCandidateError",
    "InvalidFuturesRecommendationGenerationError",
    "InvalidFuturesRecommendationGenerationPolicyError",
    "InvalidFuturesRecommendationProposalError",
    "InvalidFuturesRecommendationSessionWindowError",
    "InvalidFuturesResearchDecisionError",
    "InvalidFuturesResearchDecisionReferenceError",
    "InvalidFuturesTradeRecommendationError",
    "InvalidFuturesTradeRecommendationEventError",
    "InvalidFuturesTradeRecommendationExpiryError",
    "InvalidFuturesTradeRecommendationIdentityError",
    "InvalidFuturesTradeRecommendationLifecycleError",
    "InvalidFuturesTradeRecommendationObservationError",
    "InvalidPriceMovementUnitError",
    "InvalidPriceTargetError",
    "InvalidRecommendationPolicyVersionError",
    "InvalidRecommendationValidityError",
    "InvalidRewardToRiskError",
    "InvalidStopLossError",
    "InvalidTimeExpiryEvidenceError",
    "ObservationCoverage",
    "PriceMovementUnit",
    "PriceTarget",
    "RecommendationBoundary",
    "RecommendationEventKind",
    "RecommendationExpiryReason",
    "RecommendationPolicyVersion",
    "RecommendationStatus",
    "RecommendationValidity",
    "RewardToRisk",
    "StopLoss",
    "TimeExpiryEvidence",
    "TradeDirection",
]
