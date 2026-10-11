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

This package models no recommendation generation, price-level policy, tick
alignment, sizing, margin, persistence, publication, notification, returns or
profit and loss.
"""

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
    "CoverageDeficiency",
    "EntryZone",
    "FuturesResearchDecisionReference",
    "FuturesTradeRecommendation",
    "FuturesTradeRecommendationEvent",
    "FuturesTradeRecommendationIdentity",
    "FuturesTradeRecommendationLifecycle",
    "IntrabarOrdering",
    "InvalidEntryZoneError",
    "InvalidFuturesResearchDecisionReferenceError",
    "InvalidFuturesTradeRecommendationError",
    "InvalidFuturesTradeRecommendationEventError",
    "InvalidFuturesTradeRecommendationExpiryError",
    "InvalidFuturesTradeRecommendationIdentityError",
    "InvalidFuturesTradeRecommendationLifecycleError",
    "InvalidFuturesTradeRecommendationObservationError",
    "InvalidPriceTargetError",
    "InvalidRecommendationPolicyVersionError",
    "InvalidRecommendationValidityError",
    "InvalidStopLossError",
    "InvalidTimeExpiryEvidenceError",
    "ObservationCoverage",
    "PriceTarget",
    "RecommendationBoundary",
    "RecommendationEventKind",
    "RecommendationExpiryReason",
    "RecommendationPolicyVersion",
    "RecommendationStatus",
    "RecommendationValidity",
    "StopLoss",
    "TimeExpiryEvidence",
    "TradeDirection",
]
