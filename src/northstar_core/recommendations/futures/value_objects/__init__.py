"""Futures trade recommendation value objects."""

from .entry_zone import EntryZone, InvalidEntryZoneError
from .futures_trade_recommendation import (
    FuturesTradeRecommendation,
    InvalidFuturesTradeRecommendationError,
)
from .price_target import InvalidPriceTargetError, PriceTarget
from .recommendation_identity import (
    FuturesTradeRecommendationIdentity,
    InvalidFuturesTradeRecommendationIdentityError,
)
from .recommendation_policy_version import (
    InvalidRecommendationPolicyVersionError,
    RecommendationPolicyVersion,
)
from .recommendation_validity import InvalidRecommendationValidityError, RecommendationValidity
from .research_decision_reference import (
    FuturesResearchDecisionReference,
    InvalidFuturesResearchDecisionReferenceError,
)
from .stop_loss import InvalidStopLossError, StopLoss
from .trade_direction import TradeDirection

__all__ = [
    "EntryZone",
    "FuturesResearchDecisionReference",
    "FuturesTradeRecommendation",
    "FuturesTradeRecommendationIdentity",
    "InvalidEntryZoneError",
    "InvalidFuturesResearchDecisionReferenceError",
    "InvalidFuturesTradeRecommendationError",
    "InvalidFuturesTradeRecommendationIdentityError",
    "InvalidPriceTargetError",
    "InvalidRecommendationPolicyVersionError",
    "InvalidRecommendationValidityError",
    "InvalidStopLossError",
    "PriceTarget",
    "RecommendationPolicyVersion",
    "RecommendationValidity",
    "StopLoss",
    "TradeDirection",
]
