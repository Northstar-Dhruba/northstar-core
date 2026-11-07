"""EI-4B pure formation: exact levels, risk, costs and whole-share sizing.

Every example is synthetic. Prices, increments, rates, capital and multiples
are invented to make the arithmetic checkable by hand; none is an exchange
fact, a broker tariff or an approved trading parameter.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from fractions import Fraction

import pytest

from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.value_objects import (
    Currency,
    ExchangeCode,
    Money,
    PointInTime,
    Price,
    Symbol,
)
from northstar_core.recommendations.equity import (
    EquityCostSide,
    EquityPriceIncrement,
    EquityRecommendationDefinition,
    EquityRecommendationRejection,
    EquityRecommendationRejectionReason,
    EquityResearchCandidateReference,
    EquitySyntheticCostComponent,
    EquitySyntheticCostSchedule,
    EquitySyntheticGenerationPolicy,
    EquitySyntheticRiskPolicy,
    EquitySyntheticVersion,
    form_equity_recommendation,
)
from northstar_core.strategy import StrategyIdentity

_INR = Currency("INR")
_R = EquityRecommendationRejectionReason
_ENTRY, _EXIT = EquityCostSide.ENTRY, EquityCostSide.EXIT


def _v(name: str) -> EquitySyntheticVersion:
    return EquitySyntheticVersion(f"synthetic-{name}")


def _inr(amount: str, currency: Currency = _INR) -> Price:
    return Price(Decimal(amount), currency)


def _reference() -> EquityResearchCandidateReference:
    return EquityResearchCandidateReference(
        strategy=StrategyIdentity("synthetic-orb"),
        research_configuration_version=_v("research/1"),
        listing=ListingReference(Symbol("M&M"), ExchangeCode("NSE")),
        trading_date=date(2026, 8, 12),
        decision_as_of=PointInTime("2026-08-12T04:06:00Z"),
        research_decision_fingerprint="eir1-sha256:" + "a" * 64,
        candidate_entry_fingerprint="eirt1-sha256:" + "b" * 64,
        evidence_snapshot_id="ecs1-sha256:" + "c" * 64,
    )


def _policy(
    below: str = "0.01", above: str = "0", multiple: str = "2", minimum: str = "1"
) -> EquitySyntheticGenerationPolicy:
    return EquitySyntheticGenerationPolicy(
        _v("generation/1"), Decimal(below), Decimal(above), Decimal(multiple), Decimal(minimum)
    )


def _risk(
    capital: str = "10000", risk: str = "0.1", exposure: str = "1", currency: Currency = _INR
) -> EquitySyntheticRiskPolicy:
    return EquitySyntheticRiskPolicy(
        _v("risk/1"), Money(Decimal(capital), currency), Decimal(risk), Decimal(exposure)
    )


def _fee(
    side: EquityCostSide, rate: str = "0", per_share: str = "0", per_order: str = "0"
) -> EquitySyntheticCostComponent:
    return EquitySyntheticCostComponent(
        f"synthetic-{side.value.lower()}",
        side,
        Decimal(rate),
        Decimal(per_share),
        Decimal(per_order),
    )


def _costs(
    entry: EquitySyntheticCostComponent | None = None,
    exit_: EquitySyntheticCostComponent | None = None,
    slippage: str = "0",
    rounding: str = "0.01",
    currency: Currency = _INR,
) -> EquitySyntheticCostSchedule:
    return EquitySyntheticCostSchedule(
        _v("costs/1"),
        currency,
        (entry or _fee(_ENTRY), exit_ or _fee(_EXIT)),
        Decimal(slippage),
        Decimal(rounding),
    )


def _increment(amount: str = "1") -> EquityPriceIncrement:
    return EquityPriceIncrement(Decimal(amount), _v("increment/1"))


_UNSET = object()


def _form(  # type: ignore[no-untyped-def]
    close: str = "100",
    or_low: str = "90",
    policy=None,
    risk=_UNSET,
    increment=_UNSET,
    costs=_UNSET,
):
    return form_equity_recommendation(
        _reference(),
        _inr(close),
        _inr(or_low),
        policy or _policy(),
        _risk() if risk is _UNSET else risk,
        _increment() if increment is _UNSET else increment,
        _costs() if costs is _UNSET else costs,
    )


def _formed(**kwargs: object) -> EquityRecommendationDefinition:
    result = _form(**kwargs)
    assert isinstance(result, EquityRecommendationDefinition), result
    return result


def _reasons(**kwargs: object) -> tuple[EquityRecommendationRejectionReason, ...]:
    result = _form(**kwargs)
    assert isinstance(result, EquityRecommendationRejection), result
    return result.reasons


def _levels(definition: EquityRecommendationDefinition) -> tuple[str, str, str, str]:
    levels = definition.levels
    return tuple(  # type: ignore[return-value]
        format(price.amount, "f")
        for price in (levels.entry_zone.low, levels.entry_zone.high, levels.stop, levels.target)
    )


# -- the baseline -----------------------------------------------------------------------


def test_a_baseline_synthetic_setup_is_formed_exactly() -> None:
    definition = _formed()
    assert _levels(definition) == ("99", "100", "90", "120")
    sizing = definition.sizing
    assert sizing.quantity == 100
    assert (sizing.gross_risk, sizing.net_risk, sizing.risk_budget) == (
        Decimal("1000"),
        Decimal("1000"),
        Decimal("1000"),
    )
    assert (sizing.entry_notional, sizing.exposure_budget) == (Decimal("10000"), Decimal("10000"))
    assert (sizing.gross_reward, sizing.net_reward) == (Decimal("2000"), Decimal("2000"))
    assert definition.document()["generation_policy_version"] == "synthetic-generation/1"
    assert _form() == _form()


# -- entry zone (E, F, G) ---------------------------------------------------------------


def test_the_zone_is_aligned_inward() -> None:
    definition = _formed(
        close="100.02", or_low="90", policy=_policy("0.001", "0.001"), increment=_increment("0.05")
    )
    # 100.02 * 0.999 = 99.91998 rounds up to 99.95; 100.02 * 1.001 = 100.12002 down to 100.10.
    assert _levels(definition)[:2] == ("99.95", "100.1")


def test_a_bound_exactly_on_the_increment_is_kept() -> None:
    definition = _formed(policy=_policy("0.0005", "0"), increment=_increment("0.05"))
    assert _levels(definition)[:2] == ("99.95", "100")  # 100 * 0.9995 = 99.95 exactly
    both = _formed(policy=_policy("0.0005", "0.0005"), increment=_increment("0.05"))
    assert _levels(both)[:2] == ("99.95", "100.05")  # both bounds exactly on the grid


@pytest.mark.parametrize(
    ("close", "below", "above"),
    [
        ("100.05", "0", "0"),  # exactly on the grid, with no width
        ("100", "0.0001", "0.0001"),  # 99.99-100.01 aligns inward to 100-100
    ],
)
def test_a_zone_collapsed_to_one_grid_price_is_rejected(close: str, below: str, above: str) -> None:
    reasons = _reasons(close=close, policy=_policy(below, above), increment=_increment("0.05"))
    assert reasons == (_R.INVALID_ENTRY_ZONE,)


def test_a_zone_with_no_grid_price_left_is_rejected_never_widened() -> None:
    no_grid_price = _reasons(close="100.02", policy=_policy("0", "0"), increment=_increment("0.05"))
    assert no_grid_price == (_R.INVALID_ENTRY_ZONE,)


# -- stop (I, J, N) ---------------------------------------------------------------------


def test_the_stop_is_aligned_down_and_never_understates_risk() -> None:
    definition = _formed(or_low="90.7")
    assert _levels(definition)[2] == "90"
    assert definition.levels.risk_per_share == Decimal("10")


@pytest.mark.parametrize(
    ("or_low", "policy", "reason"),
    [
        ("100", _policy(), _R.STOP_NOT_BELOW_ENTRY),
        ("100.5", _policy(), _R.STOP_NOT_BELOW_ENTRY),
        ("99.5", _policy("0.01", "0.01"), _R.STOP_NOT_BELOW_ENTRY),  # floors to the zone low 99
        ("0.5", _policy(), _R.INVALID_PRICE),  # floors to 0
    ],
)
def test_the_stop_must_be_positive_and_below_the_whole_zone(  # type: ignore[no-untyped-def]
    or_low, policy, reason
) -> None:
    assert _reasons(or_low=or_low, policy=policy) == (reason,)


# -- target and reward-to-risk (K, L, M) ------------------------------------------------


def test_the_target_is_measured_from_the_worst_entry() -> None:
    definition = _formed(policy=_policy("0", "0.01"))
    # Zone 100-101, stop 90: risk 11 from 101, target 101 + 2 * 11 = 123 (not 100 + 2 * 10).
    assert _levels(definition) == ("100", "101", "90", "123")


def test_the_target_is_aligned_down_and_must_exceed_the_worst_entry() -> None:
    definition = _formed(policy=_policy("0", "0.01", multiple="0.33", minimum="0.1"))
    assert _levels(definition)[3] == "104"  # 101 + 0.33 * 11 = 104.63, aligned down
    assert _reasons(policy=_policy("0", "0.01", multiple="0.05")) == (_R.INVALID_TARGET,)


def test_net_reward_to_risk_is_compared_exactly() -> None:
    assert isinstance(_form(policy=_policy(minimum="2")), EquityRecommendationDefinition)
    assert _reasons(policy=_policy(minimum="2.0000000001")) == (
        _R.NET_REWARD_TO_RISK_BELOW_MINIMUM,
    )
    proportional = _costs(_fee(_ENTRY, rate="0.01"), _fee(_EXIT, rate="0.01"))
    # 84 shares: net reward 84 * (20 - 1 - 1.2) = 1495.2; net risk 84 * 11.9 = 999.6.
    accepted = _formed(policy=_policy(minimum="1.4957"), costs=proportional)
    assert (accepted.sizing.net_reward, accepted.sizing.net_risk) == (
        Decimal("1495.2"),
        Decimal("999.6"),
    )
    assert _reasons(policy=_policy(minimum="1.4958"), costs=proportional) == (
        _R.NET_REWARD_TO_RISK_BELOW_MINIMUM,
    )


# -- sizing (O, P, Q, R, S, T) ----------------------------------------------------------


def test_sizing_is_risk_limited_in_whole_shares() -> None:
    assert _formed(risk=_risk(risk="0.05")).sizing.quantity == 50
    assert _formed(risk=_risk(risk="0.0499")).sizing.quantity == 49  # budget 499


def test_sizing_is_exposure_limited() -> None:
    sizing = _formed(risk=_risk(exposure="0.3")).sizing
    assert (sizing.quantity, sizing.entry_notional) == (30, Decimal("3000"))


def test_fixed_fees_reduce_the_quantity_below_the_proportional_answer() -> None:
    fixed = _costs(_fee(_ENTRY, per_order="15"), _fee(_EXIT, per_order="15"))
    sizing = _formed(costs=fixed).sizing
    # 10q + 30 <= 1000 gives 97, where a cost-free or per-share-only reading gives 100.
    assert sizing.quantity == 97
    assert (sizing.entry_cost, sizing.stop_exit_cost, sizing.target_exit_cost) == (
        Decimal("15"),
        Decimal("15"),
        Decimal("15"),
    )
    assert (sizing.net_risk, sizing.net_reward) == (Decimal("1000"), Decimal("1910"))


def _oracle_net_risk(quantity: int) -> Fraction:
    """An independent restatement of the cost model for the mixed schedule below."""
    entry = Fraction("0.001") * 100 * quantity + Fraction("0.01") * quantity + 10
    entry += Fraction("0.0005") * 100 * quantity
    exit_ = Fraction("0.002") * 90 * quantity + Fraction("0.0005") * 90 * quantity
    ceil = lambda x: -((-x) // Fraction("0.01")) * Fraction("0.01")  # noqa: E731
    return 10 * quantity + ceil(entry) + ceil(exit_)


def test_mixed_costs_give_the_largest_quantity_within_the_budget() -> None:
    mixed = _costs(
        _fee(_ENTRY, rate="0.001", per_share="0.01", per_order="10"),
        _fee(_EXIT, rate="0.002"),
        slippage="0.0005",
    )
    sizing = _formed(costs=mixed).sizing
    quantity = sizing.quantity
    assert _oracle_net_risk(quantity) <= 1000 < _oracle_net_risk(quantity + 1)
    assert Fraction(sizing.net_risk) == _oracle_net_risk(quantity)


@pytest.mark.parametrize(
    ("risk", "reasons"),
    [
        (
            _risk(capital="100", risk="0.05"),
            (_R.NO_WHOLE_SHARE_QUANTITY, _R.INSUFFICIENT_RISK_BUDGET),
        ),
        (
            _risk(capital="50", risk="1"),
            (_R.NO_WHOLE_SHARE_QUANTITY, _R.INSUFFICIENT_EXPOSURE_BUDGET),
        ),
        (
            _risk(capital="50", risk="0.1"),
            (
                _R.NO_WHOLE_SHARE_QUANTITY,
                _R.INSUFFICIENT_RISK_BUDGET,
                _R.INSUFFICIENT_EXPOSURE_BUDGET,
            ),
        ),
    ],
)
def test_no_feasible_share_is_a_rejection_never_a_zero_share_setup(risk, reasons) -> None:  # type: ignore[no-untyped-def]
    assert _reasons(risk=risk) == reasons


def test_a_fixed_fee_larger_than_the_budget_leaves_no_share() -> None:
    heavy = _costs(_fee(_ENTRY, per_order="600"), _fee(_EXIT, per_order="600"))
    assert _reasons(costs=heavy) == (_R.NO_WHOLE_SHARE_QUANTITY, _R.INSUFFICIENT_RISK_BUDGET)


# -- unavailable and inconsistent inputs (U, ordering) ----------------------------------


def test_unavailable_inputs_are_rejected_in_order_never_defaulted() -> None:
    assert _reasons(costs=None) == (_R.COST_INPUT_UNAVAILABLE,)
    assert _reasons(increment=None) == (_R.PRICE_INCREMENT_UNAVAILABLE,)
    assert _reasons(risk=None) == (_R.RISK_POLICY_UNAVAILABLE,)
    assert _reasons(risk=None, increment=None, costs=None) == (
        _R.PRICE_INCREMENT_UNAVAILABLE,
        _R.COST_INPUT_UNAVAILABLE,
        _R.RISK_POLICY_UNAVAILABLE,
    )
    # Availability is reported before anything else is examined.
    assert _reasons(close="0", costs=None) == (_R.COST_INPUT_UNAVAILABLE,)


def test_invalid_prices_and_inconsistent_policies_are_rejected() -> None:
    usd = Currency("USD")
    assert _reasons(close="0") == (_R.INVALID_PRICE,)
    assert _reasons(or_low="0") == (_R.INVALID_PRICE,)
    mixed = form_equity_recommendation(
        _reference(), _inr("100"), _inr("90", usd), _policy(), _risk(), _increment(), _costs()
    )
    assert isinstance(mixed, EquityRecommendationRejection)
    assert mixed.reasons == (_R.INVALID_PRICE,)
    assert _reasons(risk=_risk(currency=usd)) == (_R.INVALID_SYNTHETIC_POLICY,)
    assert _reasons(costs=_costs(currency=usd)) == (_R.INVALID_SYNTHETIC_POLICY,)


def test_an_unrepresentable_level_fails_closed() -> None:
    close = "1234567890123456789012345678.9"  # 29 significant digits
    assert _reasons(close=close, or_low="1", increment=_increment("0.1")) == (
        _R.UNREPRESENTABLE_AMOUNT,
    )


def test_wrong_argument_types_are_programming_errors() -> None:
    with pytest.raises(TypeError):
        form_equity_recommendation(  # type: ignore[arg-type]
            "candidate", _inr("100"), _inr("90"), _policy(), _risk(), _increment(), _costs()
        )
    with pytest.raises(TypeError):
        form_equity_recommendation(  # type: ignore[arg-type]
            _reference(), Decimal("100"), _inr("90"), _policy(), _risk(), _increment(), _costs()
        )
    with pytest.raises(TypeError):
        form_equity_recommendation(  # type: ignore[arg-type]
            _reference(), _inr("100"), _inr("90"), None, _risk(), _increment(), _costs()
        )


def test_a_rejection_records_its_source_and_policy() -> None:
    rejection = _form(costs=None)
    assert isinstance(rejection, EquityRecommendationRejection)
    assert rejection.source == _reference()
    assert rejection.document() == {
        "source": _reference().document(),
        "generation_policy_version": "synthetic-generation/1",
        "reasons": ["COST_INPUT_UNAVAILABLE"],
    }
