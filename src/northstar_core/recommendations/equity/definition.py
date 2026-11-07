"""The structural definition of a synthetic equity recommendation (ADR-020).

An ``EquityRecommendationDefinition`` is a structurally valid, fully modeled
LONG setup: its source candidate, levels, synthetic size and the versions of
every synthetic input that produced it. It is **not** an issued
recommendation:

- it has no identity -- the Application derives one (EI-4C);
- it has no issuance or entry-eligibility instant -- see
  ``EquityRecommendationTiming`` (EI4-D1);
- it has no lifecycle state (EI-5);
- it does not mean the candidate is eligible, that any listing, timing,
  exposure or loss-limit check has passed, or that it is authoritative.

It never carries an order, fill, position or profit-and-loss amount.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.recommendations.equity._exact import is_multiple
from northstar_core.recommendations.equity.levels import (
    EquityRecommendationDirection,
    EquityRecommendationLevels,
)
from northstar_core.recommendations.equity.research_reference import (
    EquityResearchCandidateReference,
)
from northstar_core.recommendations.equity.sizing import EquitySyntheticSizing
from northstar_core.recommendations.equity.synthetic_inputs import (
    EquityPriceIncrement,
    EquitySyntheticVersion,
)


class InvalidEquityRecommendationDefinitionError(ValidationError):
    """Raised when an EquityRecommendationDefinition is internally inconsistent."""


@dataclass(frozen=True, slots=True)
class EquityRecommendationDefinition:
    """A structurally valid synthetic LONG setup. Not issued and not authoritative."""

    source: EquityResearchCandidateReference
    direction: EquityRecommendationDirection
    levels: EquityRecommendationLevels
    sizing: EquitySyntheticSizing
    price_increment: EquityPriceIncrement
    generation_policy_version: EquitySyntheticVersion
    risk_policy_version: EquitySyntheticVersion
    cost_schedule_version: EquitySyntheticVersion

    def __post_init__(self) -> None:
        error = InvalidEquityRecommendationDefinitionError
        expected = {
            "source": EquityResearchCandidateReference,
            "direction": EquityRecommendationDirection,
            "levels": EquityRecommendationLevels,
            "sizing": EquitySyntheticSizing,
            "price_increment": EquityPriceIncrement,
            "generation_policy_version": EquitySyntheticVersion,
            "risk_policy_version": EquitySyntheticVersion,
            "cost_schedule_version": EquitySyntheticVersion,
        }
        for name, kind in expected.items():
            if not isinstance(getattr(self, name), kind):
                raise error(f"EquityRecommendationDefinition {name} must be a {kind.__name__}.")
        if self.direction is not EquityRecommendationDirection.LONG:
            raise error("Equity recommendations are LONG only (EI0-D3).")
        levels, sizing = self.levels, self.sizing
        if sizing.currency != levels.currency:
            raise error("Sizing and levels must share one currency.")
        increment = self.price_increment.amount
        prices = (levels.entry_zone.low, levels.entry_zone.high, levels.stop, levels.target)
        if not all(is_multiple(price.amount, increment) for price in prices):
            raise error("Every level must be an exact multiple of the price increment.")
        quantity = sizing.quantity
        worst = Fraction(levels.worst_entry.amount)
        if (
            Fraction(sizing.entry_notional) != worst * quantity
            or Fraction(sizing.gross_risk) != (worst - Fraction(levels.stop.amount)) * quantity
            or Fraction(sizing.gross_reward) != (Fraction(levels.target.amount) - worst) * quantity
        ):
            raise error("Sizing must be measured from these levels at the worst entry.")
        if sizing.net_reward <= 0:
            raise error("A setup needs a positive net modeled reward.")

    def document(self) -> dict[str, Any]:
        """Return the canonical content, for later identity and audit."""
        return {
            "source": self.source.document(),
            "direction": self.direction.value,
            "levels": self.levels.document(),
            "sizing": self.sizing.document(),
            "price_increment": self.price_increment.document(),
            "generation_policy_version": self.generation_policy_version.value,
            "risk_policy_version": self.risk_policy_version.value,
            "cost_schedule_version": self.cost_schedule_version.value,
        }
