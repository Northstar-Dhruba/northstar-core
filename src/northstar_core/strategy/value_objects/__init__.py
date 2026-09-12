"""Strategy-specific Value Objects for the Strategy bounded context."""

from .asset_analysis import AssetAnalysis, InvalidAssetAnalysisError
from .market_observation_context import (
    InvalidMarketObservationContextError,
    MarketObservationContext,
)
from .recommendation import (
    InvalidRecommendationActionError,
    InvalidRecommendationError,
    Recommendation,
    RecommendationAction,
)
from .recommendation_explanation import (
    ExplanationReason,
    InvalidExplanationReasonError,
    InvalidRecommendationExplanationError,
    RecommendationExplanation,
)
from .strategy_identity import InvalidStrategyIdentityError, StrategyIdentity

__all__ = [
    "AssetAnalysis",
    "ExplanationReason",
    "InvalidAssetAnalysisError",
    "InvalidExplanationReasonError",
    "InvalidMarketObservationContextError",
    "InvalidRecommendationActionError",
    "InvalidRecommendationError",
    "InvalidRecommendationExplanationError",
    "InvalidStrategyIdentityError",
    "MarketObservationContext",
    "Recommendation",
    "RecommendationAction",
    "RecommendationExplanation",
    "StrategyIdentity",
]
