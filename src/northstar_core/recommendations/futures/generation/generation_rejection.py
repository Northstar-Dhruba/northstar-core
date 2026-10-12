"""Why a recommendation candidate produced no proposal.

Every candidate of a selection ends as exactly one proposal or one rejection.
A rejection names exactly one GenerationRejectionReason: generation checks the
reasons in this fixed priority and records the first that applies (ADR-018):

Per candidate
 1. STRATEGY_NOT_APPROVED           -- not the policy's approved strategy;
 2. MISSING_SESSION_WINDOW          -- no validity window for its contract;
 3. CONTRACT_EXPIRED                -- the contract ends before eligibility;
 4. INSUFFICIENT_CONTRACT_LIFE      -- the full window ends after the contract;
Per product, over the remaining (eligible) candidates
 5. CONTRADICTORY_PRODUCT_DIRECTION -- eligible expiries disagree, BUY and SELL;
 6. SHORT_NOT_ENABLED               -- SELL while the policy disables SHORT;
 7. NOT_NEAREST_ELIGIBLE_CONTRACT   -- a nearer eligible expiry was selected;
On the selected candidate
 8. CONTRADICTS_OPEN_RECOMMENDATION -- an open opposite setup on the product,
                                       on any of its expiries;
 9. DUPLICATE_OPEN_RECOMMENDATION   -- an open same-direction setup on the
                                       product, on any of its expiries;
10. MISSING_MARKET_EVIDENCE         -- no frozen evidence was supplied;
11. INSUFFICIENT_HISTORY            -- fewer than N + 1 closes;
12. ZERO_PRICE_MOVEMENT_UNIT        -- every close-to-close change is zero;
13. DEGENERATE_ENTRY_ZONE           -- inward alignment empties the zone;
14. INVALID_PRICE_ORDER             -- a level collapses onto the zone;
15. INSUFFICIENT_REWARD_TO_RISK     -- below the policy minimum.

A rejection keeps the whole candidate, so reference, research action, strategy
and analysis are never lost. Invalid or contradictory input is never a
rejection: generation raises for it instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.recommendations.futures.selection import FuturesRecommendationCandidate
from northstar_core.recommendations.futures.value_objects import (
    FuturesResearchDecisionReference,
)


class GenerationRejectionReason(StrEnum):
    """Closed vocabulary for why a candidate produced no proposal, by priority."""

    STRATEGY_NOT_APPROVED = "STRATEGY_NOT_APPROVED"
    MISSING_SESSION_WINDOW = "MISSING_SESSION_WINDOW"
    CONTRACT_EXPIRED = "CONTRACT_EXPIRED"
    INSUFFICIENT_CONTRACT_LIFE = "INSUFFICIENT_CONTRACT_LIFE"
    CONTRADICTORY_PRODUCT_DIRECTION = "CONTRADICTORY_PRODUCT_DIRECTION"
    SHORT_NOT_ENABLED = "SHORT_NOT_ENABLED"
    NOT_NEAREST_ELIGIBLE_CONTRACT = "NOT_NEAREST_ELIGIBLE_CONTRACT"
    CONTRADICTS_OPEN_RECOMMENDATION = "CONTRADICTS_OPEN_RECOMMENDATION"
    DUPLICATE_OPEN_RECOMMENDATION = "DUPLICATE_OPEN_RECOMMENDATION"
    MISSING_MARKET_EVIDENCE = "MISSING_MARKET_EVIDENCE"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    ZERO_PRICE_MOVEMENT_UNIT = "ZERO_PRICE_MOVEMENT_UNIT"
    DEGENERATE_ENTRY_ZONE = "DEGENERATE_ENTRY_ZONE"
    INVALID_PRICE_ORDER = "INVALID_PRICE_ORDER"
    INSUFFICIENT_REWARD_TO_RISK = "INSUFFICIENT_REWARD_TO_RISK"


class InvalidFuturesGenerationRejectionError(ValidationError):
    """Raised when a FuturesGenerationRejection value is invalid."""


@dataclass(frozen=True, slots=True)
class FuturesGenerationRejection:
    """Immutable candidate that produced no proposal, with its single reason."""

    candidate: FuturesRecommendationCandidate
    reason: GenerationRejectionReason

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, FuturesRecommendationCandidate):
            raise InvalidFuturesGenerationRejectionError(
                "FuturesGenerationRejection candidate must be a "
                "FuturesRecommendationCandidate value."
            )
        if not isinstance(self.reason, GenerationRejectionReason):
            raise InvalidFuturesGenerationRejectionError(
                "FuturesGenerationRejection reason must be a GenerationRejectionReason value."
            )

    @property
    def source(self) -> FuturesResearchDecisionReference:
        """Return the natural key of the rejected candidate's research decision."""
        return self.candidate.source

    def __str__(self) -> str:
        return f"rejected {self.candidate.decision}: {self.reason}"

    def __repr__(self) -> str:
        return f"FuturesGenerationRejection(candidate={self.candidate!r}, reason={self.reason!r})"
