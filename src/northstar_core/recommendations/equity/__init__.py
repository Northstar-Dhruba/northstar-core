"""Equity trade recommendation bounded context package (ADR-020).

Synthetic-only, LONG-only Core contracts for turning one EI-3 research
candidate on an NSE cash-equity listing into a modeled recommendation setup:

- versioned synthetic inputs -- ``EquitySyntheticVersion``, the price
  increment, the generation policy, the risk policy and the cost schedule
  (EI4-D4); none is an exchange fact, broker tariff or approved parameter;
- a by-value reference to the research candidate (EI4-D2); Core cannot
  verify that it is the authoritative first CANDIDATE;
- modeled levels: an entry zone anchored to the signal close (EI0-D14), a stop
  from the opening-range low and a target at a fixed multiple of worst-entry
  risk (EI4-D3), all aligned exactly to the increment;
- synthetic whole-share sizing with modeled costs, risk and reward;
- the decision, issuance and entry-eligibility instants (EI4-D1);
- ``form_equity_recommendation``, a pure function returning a structural
  ``EquityRecommendationDefinition`` or an ``EquityRecommendationRejection``.

A definition is not eligible, issued or authoritative, and has no identity or
lifecycle. Modeled levels are not fills. This package models no order, fill,
position, portfolio, profit and loss, persistence or lifecycle, reads no clock
and generates no identifier. It may build on Foundation, Domain and Strategy;
it never imports the Futures recommendation package, Derivatives, Futures,
Paper Trading or Broker Execution, and no other Core package imports it.
"""

from northstar_core.recommendations.equity.cost_schedule import (
    EquityCostSide,
    EquitySyntheticCostComponent,
    EquitySyntheticCostSchedule,
    InvalidEquitySyntheticCostScheduleError,
)
from northstar_core.recommendations.equity.definition import (
    EquityRecommendationDefinition,
    InvalidEquityRecommendationDefinitionError,
)
from northstar_core.recommendations.equity.formation import form_equity_recommendation
from northstar_core.recommendations.equity.levels import (
    EquityEntryZone,
    EquityRecommendationDirection,
    EquityRecommendationLevels,
    InvalidEquityRecommendationLevelsError,
)
from northstar_core.recommendations.equity.rejection import (
    EquityRecommendationRejection,
    EquityRecommendationRejectionReason,
    InvalidEquityRecommendationRejectionError,
)
from northstar_core.recommendations.equity.research_reference import (
    EquityResearchCandidateReference,
    InvalidEquityResearchCandidateReferenceError,
)
from northstar_core.recommendations.equity.sizing import (
    EquitySyntheticSizing,
    InvalidEquitySyntheticSizingError,
)
from northstar_core.recommendations.equity.synthetic_inputs import (
    EquityPriceIncrement,
    EquitySyntheticGenerationPolicy,
    EquitySyntheticRiskPolicy,
    EquitySyntheticVersion,
    InvalidEquityPriceIncrementError,
    InvalidEquitySyntheticGenerationPolicyError,
    InvalidEquitySyntheticRiskPolicyError,
    InvalidEquitySyntheticVersionError,
)
from northstar_core.recommendations.equity.timing import (
    EquityIssuanceKind,
    EquityRecommendationTiming,
    InvalidEquityRecommendationTimingError,
)

__all__ = [
    "EquityCostSide",
    "EquityEntryZone",
    "EquityIssuanceKind",
    "EquityPriceIncrement",
    "EquityRecommendationDefinition",
    "EquityRecommendationDirection",
    "EquityRecommendationLevels",
    "EquityRecommendationRejection",
    "EquityRecommendationRejectionReason",
    "EquityRecommendationTiming",
    "EquityResearchCandidateReference",
    "EquitySyntheticCostComponent",
    "EquitySyntheticCostSchedule",
    "EquitySyntheticGenerationPolicy",
    "EquitySyntheticRiskPolicy",
    "EquitySyntheticSizing",
    "EquitySyntheticVersion",
    "InvalidEquityPriceIncrementError",
    "InvalidEquityRecommendationDefinitionError",
    "InvalidEquityRecommendationLevelsError",
    "InvalidEquityRecommendationRejectionError",
    "InvalidEquityRecommendationTimingError",
    "InvalidEquityResearchCandidateReferenceError",
    "InvalidEquitySyntheticCostScheduleError",
    "InvalidEquitySyntheticGenerationPolicyError",
    "InvalidEquitySyntheticRiskPolicyError",
    "InvalidEquitySyntheticSizingError",
    "InvalidEquitySyntheticVersionError",
    "form_equity_recommendation",
]
