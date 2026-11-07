"""Deterministic reasons an equity recommendation cannot be formed (ADR-020).

These are ordinary, expected outcomes of pure formation -- an unavailable
synthetic input, an invalid price, a level that cannot be built, a budget that
admits no whole share -- not programming errors, which raise. The reasons are
declared in the order formation checks them, and a rejection lists them in
that order.

SIZING_SEARCH_LIMIT_EXCEEDED means the exact reward-to-risk search would have
to examine more candidate quantities than its fixed bound. Formation fails
closed rather than report a quantity it has not verified (see ``sizing``).

Application-level reasons -- listing eligibility, research timing, session
cutoffs, open recommendations -- are not formation reasons and do not appear
here (EI-4C).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.recommendations.equity.research_reference import (
    EquityResearchCandidateReference,
)
from northstar_core.recommendations.equity.synthetic_inputs import EquitySyntheticVersion


class InvalidEquityRecommendationRejectionError(ValidationError):
    """Raised when an EquityRecommendationRejection is internally inconsistent."""


class EquityRecommendationRejectionReason(StrEnum):
    """Why a setup cannot be formed, in the order formation checks."""

    PRICE_INCREMENT_UNAVAILABLE = "PRICE_INCREMENT_UNAVAILABLE"
    COST_INPUT_UNAVAILABLE = "COST_INPUT_UNAVAILABLE"
    RISK_POLICY_UNAVAILABLE = "RISK_POLICY_UNAVAILABLE"
    INVALID_PRICE = "INVALID_PRICE"
    INVALID_SYNTHETIC_POLICY = "INVALID_SYNTHETIC_POLICY"
    INVALID_ENTRY_ZONE = "INVALID_ENTRY_ZONE"
    STOP_NOT_BELOW_ENTRY = "STOP_NOT_BELOW_ENTRY"
    INVALID_TARGET = "INVALID_TARGET"
    UNREPRESENTABLE_AMOUNT = "UNREPRESENTABLE_AMOUNT"
    NO_WHOLE_SHARE_QUANTITY = "NO_WHOLE_SHARE_QUANTITY"
    INSUFFICIENT_RISK_BUDGET = "INSUFFICIENT_RISK_BUDGET"
    INSUFFICIENT_EXPOSURE_BUDGET = "INSUFFICIENT_EXPOSURE_BUDGET"
    NET_REWARD_TO_RISK_BELOW_MINIMUM = "NET_REWARD_TO_RISK_BELOW_MINIMUM"
    SIZING_SEARCH_LIMIT_EXCEEDED = "SIZING_SEARCH_LIMIT_EXCEEDED"


_ORDER = tuple(EquityRecommendationRejectionReason)


def ordered(
    reasons: set[EquityRecommendationRejectionReason],
) -> tuple[EquityRecommendationRejectionReason, ...]:
    """Return ``reasons`` in declaration order."""
    return tuple(reason for reason in _ORDER if reason in reasons)


@dataclass(frozen=True, slots=True)
class EquityRecommendationRejection:
    """A candidate for which no setup could be formed, with every reason found."""

    source: EquityResearchCandidateReference
    generation_policy_version: EquitySyntheticVersion
    reasons: tuple[EquityRecommendationRejectionReason, ...]

    def __post_init__(self) -> None:
        error = InvalidEquityRecommendationRejectionError
        if not isinstance(self.source, EquityResearchCandidateReference):
            raise error("A rejection's source must be an EquityResearchCandidateReference.")
        if not isinstance(self.generation_policy_version, EquitySyntheticVersion):
            raise error("A rejection's policy version must be an EquitySyntheticVersion.")
        reasons = self.reasons
        if not isinstance(reasons, tuple) or not reasons:
            raise error("A rejection needs a non-empty tuple of reasons.")
        if not all(isinstance(r, EquityRecommendationRejectionReason) for r in reasons):
            raise error("Rejection reasons must be EquityRecommendationRejectionReason values.")
        if reasons != ordered(set(reasons)) or len(set(reasons)) != len(reasons):
            raise error("Rejection reasons must be distinct and in declaration order.")

    def document(self) -> dict[str, Any]:
        """Return the canonical content."""
        return {
            "source": self.source.document(),
            "generation_policy_version": self.generation_policy_version.value,
            "reasons": [reason.value for reason in self.reasons],
        }
