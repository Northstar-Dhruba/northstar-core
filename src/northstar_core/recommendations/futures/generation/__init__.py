"""Futures recommendation generation and risk validation (ADR-018)."""

from .candidate_evidence import FuturesCandidateEvidence, InvalidFuturesCandidateEvidenceError
from .generation_policy import (
    FuturesRecommendationGenerationPolicy,
    InvalidFuturesRecommendationGenerationPolicyError,
)
from .generation_rejection import (
    FuturesGenerationRejection,
    GenerationRejectionReason,
    InvalidFuturesGenerationRejectionError,
)
from .recommendation_generation import (
    FuturesRecommendationGeneration,
    InvalidFuturesRecommendationGenerationError,
)
from .recommendation_proposal import (
    FuturesRecommendationProposal,
    InvalidFuturesRecommendationProposalError,
)
from .reward_to_risk import (
    InvalidPriceMovementUnitError,
    InvalidRewardToRiskError,
    PriceMovementUnit,
    RewardToRisk,
)
from .session_window import (
    FuturesRecommendationSessionWindow,
    InvalidFuturesRecommendationSessionWindowError,
)

__all__ = [
    "FuturesCandidateEvidence",
    "FuturesGenerationRejection",
    "FuturesRecommendationGeneration",
    "FuturesRecommendationGenerationPolicy",
    "FuturesRecommendationProposal",
    "FuturesRecommendationSessionWindow",
    "GenerationRejectionReason",
    "InvalidFuturesCandidateEvidenceError",
    "InvalidFuturesGenerationRejectionError",
    "InvalidFuturesRecommendationGenerationError",
    "InvalidFuturesRecommendationGenerationPolicyError",
    "InvalidFuturesRecommendationProposalError",
    "InvalidFuturesRecommendationSessionWindowError",
    "InvalidPriceMovementUnitError",
    "InvalidRewardToRiskError",
    "PriceMovementUnit",
    "RewardToRisk",
]
