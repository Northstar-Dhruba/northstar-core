"""Pure formation of a synthetic LONG equity setup from one research candidate (ADR-020).

``form_equity_recommendation`` turns research values of one candidate -- the
EI-3A signal close and opening-range low -- into either an
``EquityRecommendationDefinition`` or an ``EquityRecommendationRejection``,
under explicit synthetic inputs:

1. **Availability.** A missing price increment, cost schedule or risk policy
   is a rejection, never a default (EI4-D4).
2. **Prices.** Both research prices must be positive and in one currency.
3. **Consistency.** The risk policy and cost schedule must be in that currency.
4. **Entry zone** (EI0-D14): ``[close * (1 - below), close * (1 + above)]``,
   aligned inward -- the low up and the high down to the increment. The zone
   must keep a positive width: one collapsed to a single grid price, or left
   with no grid price at all, is INVALID_ENTRY_ZONE. It is never widened.
5. **Stop** (EI4-D3): the opening-range low aligned down, so alignment never
   moves it toward the entry or understates risk. It must be positive
   (INVALID_PRICE) and strictly below the whole zone (STOP_NOT_BELOW_ENTRY).
6. **Target** (EI4-D3): ``W + multiple * (W - stop)`` from the worst entry
   ``W`` (the zone's high), aligned down, so alignment never overstates reward.
   It must be strictly above ``W`` (INVALID_TARGET).
7. Every level must be exactly representable (UNREPRESENTABLE_AMOUNT).
8. **Size and net reward-to-risk** (``size_long_setup``): the largest whole
   number of shares within the risk and exposure budgets whose net modeled
   reward is at least the policy minimum times its net modeled risk, compared
   exactly. A smaller quantity is chosen when cost rounding makes a larger one
   fail.

Each step runs only when the earlier ones pass, and a rejection lists every
reason of the first failing step, in declaration order. Arithmetic is exact
rational arithmetic throughout. A passing result is a structural definition
only: it is not eligible, issued or authoritative, and listing, timing,
exposure and loss-limit checks belong to the Application (EI-4C).

Wrong argument types are programming errors and raise TypeError.
"""

from __future__ import annotations

from fractions import Fraction

from northstar_core.foundation.value_objects import Price
from northstar_core.recommendations.equity._exact import ceil_to, floor_to, to_decimal
from northstar_core.recommendations.equity.cost_schedule import EquitySyntheticCostSchedule
from northstar_core.recommendations.equity.definition import EquityRecommendationDefinition
from northstar_core.recommendations.equity.levels import (
    EquityEntryZone,
    EquityRecommendationDirection,
    EquityRecommendationLevels,
)
from northstar_core.recommendations.equity.rejection import (
    EquityRecommendationRejection,
    EquityRecommendationRejectionReason,
)
from northstar_core.recommendations.equity.research_reference import (
    EquityResearchCandidateReference,
)
from northstar_core.recommendations.equity.sizing import size_long_setup
from northstar_core.recommendations.equity.synthetic_inputs import (
    EquityPriceIncrement,
    EquitySyntheticGenerationPolicy,
    EquitySyntheticRiskPolicy,
)

Reason = EquityRecommendationRejectionReason


def _require(value: object, kind: type, name: str, *, optional: bool = False) -> None:
    if optional and value is None:
        return
    if not isinstance(value, kind):
        raise TypeError(f"{name} must be a {kind.__name__}{' or None' if optional else ''}.")


def form_equity_recommendation(
    source: EquityResearchCandidateReference,
    signal_close: Price,
    opening_range_low: Price,
    generation_policy: EquitySyntheticGenerationPolicy,
    risk_policy: EquitySyntheticRiskPolicy | None,
    price_increment: EquityPriceIncrement | None,
    cost_schedule: EquitySyntheticCostSchedule | None,
) -> EquityRecommendationDefinition | EquityRecommendationRejection:
    """Return the setup formed from ``source``, or the reasons none can be formed."""
    _require(source, EquityResearchCandidateReference, "source")
    _require(signal_close, Price, "signal_close")
    _require(opening_range_low, Price, "opening_range_low")
    _require(generation_policy, EquitySyntheticGenerationPolicy, "generation_policy")
    _require(risk_policy, EquitySyntheticRiskPolicy, "risk_policy", optional=True)
    _require(price_increment, EquityPriceIncrement, "price_increment", optional=True)
    _require(cost_schedule, EquitySyntheticCostSchedule, "cost_schedule", optional=True)

    def reject(*reasons: EquityRecommendationRejectionReason) -> EquityRecommendationRejection:
        return EquityRecommendationRejection(
            source, generation_policy.version, tuple(r for r in Reason if r in reasons)
        )

    missing = []
    if price_increment is None:
        missing.append(Reason.PRICE_INCREMENT_UNAVAILABLE)
    if cost_schedule is None:
        missing.append(Reason.COST_INPUT_UNAVAILABLE)
    if risk_policy is None:
        missing.append(Reason.RISK_POLICY_UNAVAILABLE)
    if missing:
        return reject(*missing)
    assert price_increment is not None and cost_schedule is not None and risk_policy is not None

    currency = signal_close.currency
    if (
        signal_close.amount <= 0
        or opening_range_low.amount <= 0
        or opening_range_low.currency != currency
    ):
        return reject(Reason.INVALID_PRICE)
    if risk_policy.currency != currency or cost_schedule.currency != currency:
        return reject(Reason.INVALID_SYNTHETIC_POLICY)

    step = Fraction(price_increment.amount)
    close = Fraction(signal_close.amount)
    low = ceil_to(close * (1 - Fraction(generation_policy.entry_offset_below)), step)
    high = floor_to(close * (1 + Fraction(generation_policy.entry_offset_above)), step)
    if low >= high:
        return reject(Reason.INVALID_ENTRY_ZONE)

    stop = floor_to(Fraction(opening_range_low.amount), step)
    if stop <= 0:
        return reject(Reason.INVALID_PRICE)
    if stop >= low:
        return reject(Reason.STOP_NOT_BELOW_ENTRY)

    risk_per_share = high - stop
    target = floor_to(
        high + Fraction(generation_policy.target_risk_multiple) * risk_per_share, step
    )
    if target <= high:
        return reject(Reason.INVALID_TARGET)

    amounts = [to_decimal(value) for value in (low, high, stop, target)]
    if any(amount is None for amount in amounts):
        return reject(Reason.UNREPRESENTABLE_AMOUNT)
    low_price, high_price, stop_price, target_price = (
        Price(amount, currency)
        for amount in amounts  # type: ignore[arg-type]
    )
    levels = EquityRecommendationLevels(
        EquityEntryZone(low_price, high_price), stop_price, target_price
    )

    sizing = size_long_setup(
        levels, risk_policy, cost_schedule, generation_policy.minimum_net_reward_to_risk
    )
    if isinstance(sizing, tuple):
        return reject(*sizing)

    return EquityRecommendationDefinition(
        source=source,
        direction=EquityRecommendationDirection.LONG,
        levels=levels,
        sizing=sizing,
        price_increment=price_increment,
        generation_policy_version=generation_policy.version,
        risk_policy_version=risk_policy.version,
        cost_schedule_version=cost_schedule.version,
    )
