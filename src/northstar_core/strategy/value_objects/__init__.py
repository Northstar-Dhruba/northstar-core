"""Strategy-specific Value Objects for the Strategy bounded context."""

from .asset_analysis import AssetAnalysis, InvalidAssetAnalysisError
from .futures_asset_analysis import (
    FuturesAssetAnalysis,
    InvalidFuturesAssetAnalysisError,
)
from .futures_market_observation_context import (
    FuturesMarketObservationContext,
    InvalidFuturesMarketObservationContextError,
)
from .futures_recommendation import (
    FuturesRecommendation,
    InvalidFuturesRecommendationError,
)
from .futures_recommendation_outcome import (
    FuturesRecommendationOutcome,
    FuturesRecommendationOutcomeUnavailableReason,
    InvalidFuturesRecommendationOutcomeError,
)
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
from .recommendation_outcome import (
    InvalidRecommendationOutcomeError,
    RecommendationOutcome,
)
from .research_horizon import InvalidResearchHorizonError, ResearchHorizon
from .strategy_identity import InvalidStrategyIdentityError, StrategyIdentity

__all__ = [
    "AssetAnalysis",
    "InvalidFuturesRecommendationError",
    "InvalidFuturesMarketObservationContextError",
    "InvalidFuturesAssetAnalysisError",
    "FuturesRecommendation",
    "FuturesMarketObservationContext",
    "FuturesAssetAnalysis",
    "FuturesRecommendationOutcome",
    "FuturesRecommendationOutcomeUnavailableReason",
    "InvalidFuturesRecommendationOutcomeError",
    "ExplanationReason",
    "InvalidAssetAnalysisError",
    "InvalidExplanationReasonError",
    "InvalidMarketObservationContextError",
    "InvalidRecommendationActionError",
    "InvalidRecommendationError",
    "InvalidRecommendationExplanationError",
    "InvalidRecommendationOutcomeError",
    "InvalidResearchHorizonError",
    "InvalidStrategyIdentityError",
    "MarketObservationContext",
    "Recommendation",
    "RecommendationAction",
    "RecommendationExplanation",
    "RecommendationOutcome",
    "ResearchHorizon",
    "StrategyIdentity",
]
