"""EI-4B sizing: the largest quantity meeting the budgets and the net reward-to-risk minimum.

Cost rounding makes the net reward-to-risk margin non-monotonic in quantity, so
the largest quantity within budget may fail where a smaller one passes. These
tests check the exact search against an independent exhaustive oracle.

Every value is synthetic: levels, rates, fees, rounding, capital and minimums
are invented for checkable arithmetic and approve nothing.
"""

from __future__ import annotations

import itertools
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
from northstar_core.recommendations.equity import sizing as sizing_module
from northstar_core.strategy import StrategyIdentity

_INR = Currency("INR")
_R = EquityRecommendationRejectionReason
# The synthetic levels every case uses: zone 99-100, worst entry W = 100, stop
# S = 90 and, with a target multiple of 2, target T = 120.
_W, _S, _T = Fraction(100), Fraction(90), Fraction(120)


def _v(name: str) -> EquitySyntheticVersion:
    return EquitySyntheticVersion(f"synthetic-{name}")


def _reference() -> EquityResearchCandidateReference:
    return EquityResearchCandidateReference(
        StrategyIdentity("synthetic-orb"),
        _v("research/1"),
        ListingReference(Symbol("M&M"), ExchangeCode("NSE")),
        date(2026, 8, 12),
        PointInTime("2026-08-12T04:06:00Z"),
        "eir1-sha256:" + "a" * 64,
        "eirt1-sha256:" + "b" * 64,
        "ecs1-sha256:" + "c" * 64,
    )


def _schedule(
    entry: tuple[str, str, str], exit_: tuple[str, str, str], slippage: str, rounding: str
) -> EquitySyntheticCostSchedule:
    def component(side: EquityCostSide, terms: tuple[str, str, str]):  # type: ignore[no-untyped-def]
        rate, per_share, per_order = (Decimal(t) for t in terms)
        return EquitySyntheticCostComponent(
            f"synthetic-{side.value.lower()}", side, rate, per_share, per_order
        )

    return EquitySyntheticCostSchedule(
        _v("costs/1"),
        _INR,
        (component(EquityCostSide.ENTRY, entry), component(EquityCostSide.EXIT, exit_)),
        Decimal(slippage),
        Decimal(rounding),
    )


def _form(  # type: ignore[no-untyped-def]
    minimum: str,
    capital: str,
    entry=("0", "0", "0"),
    exit_=("0", "0", "0"),
    slippage="0",
    rounding="0.01",
    risk="0.1",
    exposure="1",
):
    return form_equity_recommendation(
        _reference(),
        Price(Decimal("100"), _INR),
        Price(Decimal("90"), _INR),
        EquitySyntheticGenerationPolicy(
            _v("generation/1"), Decimal("0.01"), Decimal("0"), Decimal("2"), Decimal(minimum)
        ),
        EquitySyntheticRiskPolicy(
            _v("risk/1"), Money(Decimal(capital), _INR), Decimal(risk), Decimal(exposure)
        ),
        EquityPriceIncrement(Decimal("1"), _v("increment/1")),
        _schedule(entry, exit_, slippage, rounding),
    )


# -- the independent oracle -------------------------------------------------------------


def _ceil(value: Fraction, step: Fraction) -> Fraction:
    return -((-value) // step) * step


def _cost(terms: tuple[str, str, str], slippage: str, rounding: str, price: Fraction, q: int):  # type: ignore[no-untyped-def]
    rate, per_share, per_order = (Fraction(t) for t in terms)
    total = (rate + Fraction(slippage)) * price * q + per_share * q + per_order
    return _ceil(total, Fraction(rounding))


def _oracle_checks(  # type: ignore[no-untyped-def]
    q, minimum, capital, entry, exit_, slippage, rounding, risk="0.1", exposure="1"
) -> tuple[bool, bool]:
    """Return (within budgets, meets the minimum) for ``q`` shares, from first principles."""
    entry_cost = _cost(entry, slippage, rounding, _W, q)
    stop_exit = _cost(exit_, slippage, rounding, _S, q)
    target_exit = _cost(exit_, slippage, rounding, _T, q)
    net_risk = q * (_W - _S) + entry_cost + stop_exit
    net_reward = q * (_T - _W) - entry_cost - target_exit
    budget = Fraction(capital) * Fraction(risk)
    within = net_risk <= budget and q * _W <= Fraction(capital) * Fraction(exposure)
    return within, net_reward >= Fraction(minimum) * net_risk


def _oracle(minimum, capital, entry, exit_, slippage, rounding):  # type: ignore[no-untyped-def]
    """Return the largest passing whole-share quantity by exhaustive search, or None."""
    best = None
    for q in range(1, int(Fraction(capital) // _W) + 1):
        within, meets = _oracle_checks(q, minimum, capital, entry, exit_, slippage, rounding)
        if within and meets:
            best = q
    return best


# -- regression cases -------------------------------------------------------------------


def test_a_smaller_quantity_is_chosen_when_rounding_fails_the_largest() -> None:
    entry = ("0.003", "0", "0")
    # Within budget: 11 shares (net risk 110 + ceil(3.3) = 114 = the budget).
    assert _oracle_checks(11, "1.9", "1140", entry, ("0", "0", "0"), "0", "1") == (True, False)
    assert _oracle_checks(10, "1.9", "1140", entry, ("0", "0", "0"), "0", "1") == (True, True)
    result = _form("1.9", "1140", entry=entry, rounding="1")
    assert isinstance(result, EquityRecommendationDefinition)
    sizing = result.sizing
    assert sizing.quantity == 10
    assert (sizing.entry_cost, sizing.net_risk, sizing.net_reward) == (
        Decimal("3"),
        Decimal("103"),
        Decimal("197"),
    )


def test_the_largest_quantity_is_kept_when_it_passes() -> None:
    result = _form("1", "10000")
    assert isinstance(result, EquityRecommendationDefinition)
    assert result.sizing.quantity == 100


def test_no_quantity_passes_when_fixed_fees_outweigh_the_margin_within_budget() -> None:
    fees = ("0", "0", "100")
    # Margin 10q - 400 needs q >= 40; the budget of 500 allows only 30.
    assert _oracle("1", "5000", fees, fees, "0", "0.01") is None
    result = _form("1", "5000", entry=fees, exit_=fees)
    assert isinstance(result, EquityRecommendationRejection)
    assert result.reasons == (_R.NET_REWARD_TO_RISK_BELOW_MINIMUM,)


def test_fixed_and_proportional_fees_with_rounded_entry_and_exit_costs() -> None:
    entry, exit_ = ("0.003", "0.07", "1"), ("0.002", "0", "1")
    for minimum, capital in (("1.5", "1140"), ("1.8", "2500"), ("1.6", "777")):
        expected = _oracle(minimum, capital, entry, exit_, "0.0013", "1")
        result = _form(minimum, capital, entry=entry, exit_=exit_, slippage="0.0013", rounding="1")
        if expected is None:
            assert isinstance(result, EquityRecommendationRejection)
        else:
            assert isinstance(result, EquityRecommendationDefinition)
            assert result.sizing.quantity == expected


def test_a_ratio_exactly_at_the_minimum_passes_and_just_above_fails() -> None:
    per_share = ("0", "2", "0")
    # Entry costs 2 per share: net reward 18q and net risk 12q, a ratio of exactly 1.5.
    exact = _form("1.5", "10000", entry=per_share)
    assert isinstance(exact, EquityRecommendationDefinition)
    sizing = exact.sizing
    assert sizing.quantity == 83
    assert Fraction(sizing.net_reward) == Fraction("1.5") * Fraction(sizing.net_risk)
    above = _form("1.5000000001", "10000", entry=per_share)
    assert isinstance(above, EquityRecommendationRejection)
    assert above.reasons == (_R.NET_REWARD_TO_RISK_BELOW_MINIMUM,)


def test_a_very_large_budget_is_sized_without_a_linear_scan() -> None:
    result = _form("1", "1000000000000")
    assert isinstance(result, EquityRecommendationDefinition)
    assert result.sizing.quantity == 10_000_000_000


def test_a_large_budget_whose_largest_quantity_fails_finds_the_largest_passing() -> None:
    entry, nothing = ("0.003", "0", "0"), ("0", "0", "0")
    # Minimum 1.912621 leaves a tiny unrounded margin slope, so rounding decides
    # pass or fail even near a hundred thousand shares.
    minimum, capital = "1.912621", "10302000"
    result = _form(minimum, capital, entry=entry, rounding="1", risk="0.1")
    assert isinstance(result, EquityRecommendationDefinition)
    chosen = result.sizing.quantity
    within, meets = _oracle_checks(chosen, minimum, capital, entry, nothing, "0", "1")
    assert within and meets
    budget_bound = 100_019  # 10 * q + ceil(0.3 * q) <= 1,030,200 up to 100,019 shares
    assert _oracle_checks(budget_bound, minimum, capital, entry, nothing, "0", "1")[0]
    assert not _oracle_checks(budget_bound + 1, minimum, capital, entry, nothing, "0", "1")[0]
    for q in range(chosen + 1, budget_bound + 1):
        assert not _oracle_checks(q, minimum, capital, entry, nothing, "0", "1")[1], q


def test_an_oversized_search_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    # Test-only: shrink the bound so the counterexample's window of nine exceeds it.
    monkeypatch.setattr(sizing_module, "_SEARCH_LIMIT", 0)
    result = _form("1.9", "1140", entry=("0.003", "0", "0"), rounding="1")
    assert isinstance(result, EquityRecommendationRejection)
    assert result.reasons == (_R.SIZING_SEARCH_LIMIT_EXCEEDED,)


# -- exhaustive comparison --------------------------------------------------------------

_GRID = list(
    itertools.product(
        (("0", "0", "0"), ("0.003", "0", "0"), ("0.0007", "0.07", "3")),  # entry
        (("0", "0", "0"), ("0.002", "0", "2")),  # exit
        ("0", "0.0013"),  # slippage
        ("0.01", "1"),  # rounding
        ("1", "1.5", "1.9", "1.95"),  # minimum net reward-to-risk
        ("300", "1140", "2500"),  # model capital
    )
)


def test_the_search_matches_an_exhaustive_oracle() -> None:
    smaller_than_budget = 0
    for entry, exit_, slippage, rounding, minimum, capital in _GRID:
        expected = _oracle(minimum, capital, entry, exit_, slippage, rounding)
        result = _form(
            minimum, capital, entry=entry, exit_=exit_, slippage=slippage, rounding=rounding
        )
        case = (entry, exit_, slippage, rounding, minimum, capital)
        if expected is None:
            assert isinstance(result, EquityRecommendationRejection), case
            assert _R.SIZING_SEARCH_LIMIT_EXCEEDED not in result.reasons, case
        else:
            assert isinstance(result, EquityRecommendationDefinition), case
            assert result.sizing.quantity == expected, case
            within_next, _ = _oracle_checks(
                expected + 1, minimum, capital, entry, exit_, slippage, rounding
            )
            if within_next:
                smaller_than_budget += 1
    # The grid really exercises the case the budget alone would have got wrong.
    assert smaller_than_budget > 0
