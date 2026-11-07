"""Synthetic whole-share sizing of a modeled LONG setup (EI4-D4, ADR-020).

For ``q`` whole shares, worst entry ``W``, stop ``S`` and target ``T``:

    gross risk   = q * (W - S)
    net risk     = gross risk + entry cost(W, q) + exit cost(S, q)
    gross reward = q * (T - W)
    net reward   = gross reward - entry cost(W, q) - exit cost(T, q)
    notional     = q * W

The quantity is the **largest** whole number of shares satisfying every
constraint at once:

- ``net risk <= risk budget`` and ``notional <= exposure budget``, the budgets
  being the risk policy's fractions of model capital;
- ``net reward >= m * net risk``, ``m`` the policy's minimum net
  reward-to-risk (so net reward is positive, because net risk is).

Budgets
-------
Net risk and notional never decrease as ``q`` grows -- every cost term is
non-negative and rounded up -- so the quantities within budget are exactly
``1 .. Q``, and ``Q`` is found by a deterministic binary search.

Reward-to-risk
--------------
The margin ``g(q) = net reward - m * net risk`` is **not** monotonic: each
side's cost is rounded up to the schedule's increment, so a larger quantity
can lose more to rounding than a smaller one gains. It is searched exactly:

- Each side's cost is ``rho * ceil((a * q + f) / rho)``, with ``a`` the
  per-share slope, ``f`` the per-order amount and ``rho`` the rounding
  increment (``side_terms``). Let ``P`` be the least common multiple of the
  denominators of every ``a / rho``. Then ``a * P / rho`` is an integer, so
  each rounded cost satisfies ``cost(q + P) = cost(q) + a * P`` exactly, and
  ``g(q + P) = g(q) + P * k`` where ``k`` is the margin's unrounded slope
  ``(T - W) - m * (W - S) - (1 + m) * a_entry - a_target - m * a_stop``.
- Rounding only adds cost, so ``g(q) <= k * q - F`` with
  ``F = (1 + m) * (f_entry + f_exit) >= 0``.
- If ``k < 0``, no quantity passes. If ``k >= 0``, ``g`` never decreases along
  a residue class modulo ``P``: if the largest member of a class within
  ``1 .. Q`` fails, every smaller member fails too. The answer is therefore the
  largest passing ``q`` among the top ``P`` quantities ``max(1, Q - P + 1) ..
  Q``, and quantities below ``F / k`` (where ``k * q - F < 0``) never pass.
- The candidates left are examined from ``Q`` downward, at most
  ``_SEARCH_LIMIT`` of them. A larger window is a typed rejection,
  ``SIZING_SEARCH_LIMIT_EXCEEDED``: it fails closed rather than guessing.

No feasible share is a rejection, never a zero-share setup. Model capital is
not buying power, no leverage or margin is modelled, and nothing here assumes
any daily-loss or portfolio control has passed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from math import lcm
from typing import Any

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency
from northstar_core.recommendations.equity._exact import canonical, text, to_decimal
from northstar_core.recommendations.equity.cost_schedule import (
    EquityCostSide,
    EquitySyntheticCostSchedule,
    side_cost,
    side_terms,
)
from northstar_core.recommendations.equity.levels import EquityRecommendationLevels
from northstar_core.recommendations.equity.rejection import (
    EquityRecommendationRejectionReason,
    ordered,
)
from northstar_core.recommendations.equity.synthetic_inputs import EquitySyntheticRiskPolicy

_AMOUNTS = (
    "entry_notional",
    "entry_cost",
    "stop_exit_cost",
    "target_exit_cost",
    "gross_risk",
    "net_risk",
    "gross_reward",
    "net_reward",
    "risk_budget",
    "exposure_budget",
)
Reason = EquityRecommendationRejectionReason
# The most reward-to-risk candidates examined before failing closed.
_SEARCH_LIMIT = 10_000


class InvalidEquitySyntheticSizingError(ValidationError):
    """Raised when an EquitySyntheticSizing is internally inconsistent."""


@dataclass(frozen=True, slots=True)
class EquitySyntheticSizing:
    """A synthetic whole-share size with its modeled costs, risk and reward.

    Every amount is in ``currency``. It is a suggestion under synthetic
    inputs, not an order quantity or a position.
    """

    currency: Currency
    quantity: int
    entry_notional: Decimal
    entry_cost: Decimal
    stop_exit_cost: Decimal
    target_exit_cost: Decimal
    gross_risk: Decimal
    net_risk: Decimal
    gross_reward: Decimal
    net_reward: Decimal
    risk_budget: Decimal
    exposure_budget: Decimal

    def __post_init__(self) -> None:
        error = InvalidEquitySyntheticSizingError
        if not isinstance(self.currency, Currency):
            raise error("EquitySyntheticSizing currency must be a Currency.")
        quantity = self.quantity
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise error("EquitySyntheticSizing quantity must be a whole number of at least 1.")
        for name in _AMOUNTS:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Decimal) or not value.is_finite():
                raise error(f"EquitySyntheticSizing {name} must be a finite Decimal.")
            object.__setattr__(self, name, canonical(value))
        for name in ("entry_cost", "stop_exit_cost", "target_exit_cost"):
            if getattr(self, name) < 0:
                raise error(f"EquitySyntheticSizing {name} cannot be negative.")
        if self.gross_risk <= 0 or self.gross_reward <= 0:
            raise error("EquitySyntheticSizing gross risk and gross reward must be positive.")
        if self.net_risk != self.gross_risk + self.entry_cost + self.stop_exit_cost:
            raise error("Net risk must be gross risk plus entry and stop-exit costs.")
        if self.net_reward != self.gross_reward - self.entry_cost - self.target_exit_cost:
            raise error("Net reward must be gross reward less entry and target-exit costs.")
        if self.net_risk > self.risk_budget:
            raise error("Net risk must not exceed the risk budget.")
        if self.entry_notional > self.exposure_budget:
            raise error("Entry notional must not exceed the exposure budget.")

    def document(self) -> dict[str, Any]:
        """Return the canonical content."""
        return {
            "currency": self.currency.value,
            "quantity": self.quantity,
            **{name: text(getattr(self, name)) for name in _AMOUNTS},
        }


def size_long_setup(
    levels: EquityRecommendationLevels,
    risk_policy: EquitySyntheticRiskPolicy,
    schedule: EquitySyntheticCostSchedule,
    minimum_net_reward_to_risk: Decimal,
) -> EquitySyntheticSizing | tuple[EquityRecommendationRejectionReason, ...]:
    """Return the largest size meeting every constraint, or the reasons none exists.

    The caller guarantees that ``levels``, ``risk_policy`` and ``schedule``
    share one currency, and that the minimum is a positive Decimal.
    """
    worst = Fraction(levels.worst_entry.amount)
    stop = Fraction(levels.stop.amount)
    target = Fraction(levels.target.amount)
    minimum = Fraction(minimum_net_reward_to_risk)
    capital = Fraction(risk_policy.model_capital.amount)
    risk_budget = capital * Fraction(risk_policy.risk_fraction)
    exposure_budget = capital * Fraction(risk_policy.exposure_fraction)
    entry, exit_ = EquityCostSide.ENTRY, EquityCostSide.EXIT

    def costs(quantity: int) -> tuple[Fraction, Fraction, Fraction]:
        return (
            side_cost(schedule, entry, worst, quantity),
            side_cost(schedule, exit_, stop, quantity),
            side_cost(schedule, exit_, target, quantity),
        )

    def net_risk(quantity: int) -> Fraction:
        entry_cost, stop_exit, _ = costs(quantity)
        return quantity * (worst - stop) + entry_cost + stop_exit

    def margin(quantity: int) -> Fraction:
        entry_cost, stop_exit, target_exit = costs(quantity)
        reward = quantity * (target - worst) - entry_cost - target_exit
        return reward - minimum * (quantity * (worst - stop) + entry_cost + stop_exit)

    low, high = 0, min(int(exposure_budget // worst), int(risk_budget // (worst - stop)))
    while low < high:
        middle = (low + high + 1) // 2
        if net_risk(middle) <= risk_budget:
            low = middle
        else:
            high = middle - 1
    within_budget = low
    if within_budget == 0:
        reasons = {Reason.NO_WHOLE_SHARE_QUANTITY}
        if net_risk(1) > risk_budget:
            reasons.add(Reason.INSUFFICIENT_RISK_BUDGET)
        if worst > exposure_budget:
            reasons.add(Reason.INSUFFICIENT_EXPOSURE_BUDGET)
        return ordered(reasons)

    found = _largest_passing(within_budget, margin, schedule, worst, stop, target, minimum)
    if isinstance(found, EquityRecommendationRejectionReason):
        return (found,)
    quantity = found
    entry_cost, stop_exit, target_exit = costs(quantity)
    gross_risk = quantity * (worst - stop)
    gross_reward = quantity * (target - worst)
    exact = {
        "entry_notional": quantity * worst,
        "entry_cost": entry_cost,
        "stop_exit_cost": stop_exit,
        "target_exit_cost": target_exit,
        "gross_risk": gross_risk,
        "net_risk": gross_risk + entry_cost + stop_exit,
        "gross_reward": gross_reward,
        "net_reward": gross_reward - entry_cost - target_exit,
        "risk_budget": risk_budget,
        "exposure_budget": exposure_budget,
    }
    amounts = {name: to_decimal(value) for name, value in exact.items()}
    if any(value is None for value in amounts.values()):
        return (Reason.UNREPRESENTABLE_AMOUNT,)
    return EquitySyntheticSizing(
        currency=levels.currency,
        quantity=quantity,
        **amounts,  # type: ignore[arg-type]
    )


def _largest_passing(
    within_budget: int,
    margin: Callable[[int], Fraction],
    schedule: EquitySyntheticCostSchedule,
    worst: Fraction,
    stop: Fraction,
    target: Fraction,
    minimum: Fraction,
) -> int | EquityRecommendationRejectionReason:
    """Return the largest ``q`` in ``1 .. within_budget`` with ``margin(q) >= 0``.

    See the module docstring for why examining the top ``P`` quantities, and
    none below ``F / k``, is exact.
    """
    if margin(within_budget) >= 0:
        return within_budget
    rho = Fraction(schedule.rounding_increment)
    a_entry, f_entry = side_terms(schedule, EquityCostSide.ENTRY, worst)
    a_stop, f_exit = side_terms(schedule, EquityCostSide.EXIT, stop)
    a_target, _ = side_terms(schedule, EquityCostSide.EXIT, target)
    slope = (
        (target - worst)
        - minimum * (worst - stop)
        - (1 + minimum) * a_entry
        - a_target
        - minimum * a_stop
    )
    fixed = (1 + minimum) * (f_entry + f_exit)
    if slope < 0 or (slope == 0 and fixed > 0):
        return Reason.NET_REWARD_TO_RISK_BELOW_MINIMUM
    period = lcm(*((a / rho).denominator for a in (a_entry, a_stop, a_target)))
    lowest = max(1, within_budget - period + 1)
    if slope > 0:
        lowest = max(lowest, -((-fixed) // slope))
    if within_budget - lowest > _SEARCH_LIMIT:
        return Reason.SIZING_SEARCH_LIMIT_EXCEEDED
    for quantity in range(within_budget - 1, lowest - 1, -1):
        if margin(quantity) >= 0:
            return quantity
    return Reason.NET_REWARD_TO_RISK_BELOW_MINIMUM
