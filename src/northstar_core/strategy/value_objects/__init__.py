"""Strategy-specific Value Objects for the Strategy bounded context."""

from .asset_analysis import AssetAnalysis, InvalidAssetAnalysisError
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
    "InvalidRecommendationActionError",
    "InvalidRecommendationError",
    "InvalidRecommendationExplanationError",
    "InvalidStrategyIdentityError",
    "Recommendation",
    "RecommendationAction",
    "RecommendationExplanation",
    "StrategyIdentity",
]
