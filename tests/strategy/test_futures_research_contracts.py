"""Tests for the Core futures research contracts.

These cover FuturesMarketObservationContext, FuturesAssetAnalysis and
FuturesRecommendation. The quotations below include negative and zero values
deliberately: the equity contracts cannot represent them, and that is the whole
reason these parallel values exist.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from northstar_core.derivatives import ExpirationDate, QuoteValue
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import (
    ExchangeCode,
    PointInTime,
    Price,
    Quantity,
    Symbol,
    Timeframe,
)
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.strategy import (
    AssetAnalysis,
    FuturesAssetAnalysis,
    FuturesMarketObservationContext,
    FuturesRecommendation,
    InvalidFuturesAssetAnalysisError,
    InvalidFuturesMarketObservationContextError,
    InvalidFuturesRecommendationError,
    Recommendation,
    RecommendationAction,
    StrategyIdentity,
)

_CME = ExchangeCode("CME")
_NYMEX = ExchangeCode("NYMEX")

_ES = FuturesProductReference(Symbol("ES"), _CME)
_MES = FuturesProductReference(Symbol("MES"), _CME)
_CL = FuturesProductReference(Symbol("CL"), _NYMEX)

_DEC_2026 = ExpirationDate("2026-12-18")
_MAR_2027 = ExpirationDate("2027-03-19")

_ES_DEC = FuturesContract(_ES, _DEC_2026)
_ES_MAR = FuturesContract(_ES, _MAR_2027)
_MES_DEC = FuturesContract(_MES, _DEC_2026)
_CL_DEC = FuturesContract(_CL, _DEC_2026)

_DAILY = Timeframe("1d")
_INSTANT = PointInTime("2026-09-15T22:00:00Z")
_STRATEGY = StrategyIdentity("alpha")


def _quotes(*values: str) -> tuple[QuoteValue, ...]:
    return tuple(QuoteValue(Decimal(value)) for value in values)


def _series(value: str = "7660", count: int = 20) -> tuple[QuoteValue, ...]:
    return _quotes(*([value] * count))


def _volumes(count: int = 20, value: str = "1000") -> tuple[Quantity, ...]:
    return tuple(Quantity(Decimal(value)) for _ in range(count))


def _context(**overrides: object) -> FuturesMarketObservationContext:
    members: dict[str, object] = {
        "contract": _ES_DEC,
        "timeframe": _DAILY,
        "observed_at": _INSTANT,
        "latest_quote": QuoteValue(Decimal("7663")),
        "previous_close": QuoteValue(Decimal("7650")),
        "latest_volume": Quantity(Decimal("1250000")),
        "session_high": QuoteValue(Decimal("7700")),
        "session_low": QuoteValue(Decimal("7500")),
        "recent_closes": _series(),
        "recent_volumes": _volumes(),
    }
    members.update(overrides)
    return FuturesMarketObservationContext(**members)  # type: ignore[arg-type]


def _analysis(contract: FuturesContract = _ES_DEC) -> FuturesAssetAnalysis:
    return FuturesAssetAnalysis(contract, _INSTANT, ("strong bullish",))


def _recommendation(contract: FuturesContract = _ES_DEC) -> FuturesRecommendation:
    return FuturesRecommendation(
        RecommendationAction("BUY"), _analysis(contract), _STRATEGY, _INSTANT
    )


# ---------------------------------------------------------------------------
# Context: construction
# ---------------------------------------------------------------------------


def test_a_context_preserves_its_members() -> None:
    context = _context()

    assert context.contract == _ES_DEC
    assert context.timeframe == _DAILY
    assert context.observed_at == _INSTANT
    assert context.latest_quote == QuoteValue(Decimal("7663"))
    assert context.previous_close == QuoteValue(Decimal("7650"))
    assert context.latest_volume == Quantity(Decimal("1250000"))
    assert context.session_high == QuoteValue(Decimal("7700"))
    assert context.session_low == QuoteValue(Decimal("7500"))
    assert len(context.recent_closes) == 20
    assert len(context.recent_volumes) == 20


def test_the_contract_is_the_sole_subject_identity() -> None:
    context = _context()

    for absent in ("listing_reference", "symbol", "exchange_code", "provider_symbol"):
        assert not hasattr(context, absent)
    assert set(FuturesMarketObservationContext.__slots__) == {
        "contract",
        "timeframe",
        "observed_at",
        "latest_quote",
        "previous_close",
        "latest_volume",
        "session_high",
        "session_low",
        "recent_closes",
        "recent_volumes",
    }


def test_the_context_carries_no_session_calendar_detail() -> None:
    """The calendar decided which bars exist before this value was built."""
    context = _context()

    for absent in ("opens_at", "closes_at", "trading_date", "session"):
        assert not hasattr(context, absent)


# ---------------------------------------------------------------------------
# Context: warm-up
# ---------------------------------------------------------------------------


def test_twenty_observations_are_accepted() -> None:
    context = _context(recent_closes=_series(count=20), recent_volumes=_volumes(20))

    assert len(context.recent_closes) == 20


def test_nineteen_observations_are_rejected() -> None:
    with pytest.raises(
        InvalidFuturesMarketObservationContextError, match="at least 20 observations"
    ):
        _context(recent_closes=_series(count=19), recent_volumes=_volumes(19))


def test_more_than_twenty_observations_are_accepted() -> None:
    context = _context(recent_closes=_series(count=250), recent_volumes=_volumes(250))

    assert len(context.recent_closes) == 250


def test_mismatched_history_lengths_are_rejected() -> None:
    """A mismatch would silently pair a close with another observation's volume."""
    with pytest.raises(InvalidFuturesMarketObservationContextError, match="same observations"):
        _context(recent_closes=_series(count=21), recent_volumes=_volumes(20))


def test_too_few_volumes_are_rejected_by_name() -> None:
    with pytest.raises(
        InvalidFuturesMarketObservationContextError, match="recent volumes must contain"
    ):
        _context(recent_volumes=_volumes(19))


def test_observations_need_not_be_contiguous_sessions() -> None:
    """A sparse futures series is ordinary; the context stores values, not dates."""
    context = _context(recent_closes=_quotes(*[str(7600 + i) for i in range(20)]))

    assert len(context.recent_closes) == 20


# ---------------------------------------------------------------------------
# Context: session bounds
# ---------------------------------------------------------------------------


def test_a_latest_quote_below_the_session_low_is_rejected() -> None:
    with pytest.raises(
        InvalidFuturesMarketObservationContextError, match="within the session high and low"
    ):
        _context(latest_quote=QuoteValue(Decimal("7499")))


def test_a_latest_quote_above_the_session_high_is_rejected() -> None:
    with pytest.raises(
        InvalidFuturesMarketObservationContextError, match="within the session high and low"
    ):
        _context(latest_quote=QuoteValue(Decimal("7701")))


def test_a_latest_quote_exactly_on_either_bound_is_accepted() -> None:
    assert _context(latest_quote=QuoteValue(Decimal("7500"))).latest_quote == QuoteValue(
        Decimal("7500")
    )
    assert _context(latest_quote=QuoteValue(Decimal("7700"))).latest_quote == QuoteValue(
        Decimal("7700")
    )


def test_an_inverted_session_band_is_rejected() -> None:
    with pytest.raises(
        InvalidFuturesMarketObservationContextError, match="must not exceed session high"
    ):
        _context(session_high=QuoteValue(Decimal("7000")), session_low=QuoteValue(Decimal("7800")))


def test_a_flat_session_band_is_accepted() -> None:
    context = _context(
        session_high=QuoteValue(Decimal("7663")),
        session_low=QuoteValue(Decimal("7663")),
        latest_quote=QuoteValue(Decimal("7663")),
    )

    assert context.session_high == context.session_low == context.latest_quote


# ---------------------------------------------------------------------------
# Quote behaviour
# ---------------------------------------------------------------------------


def test_a_wholly_negative_session_is_valid() -> None:
    """The 2020 crude session the equity contract could not have held."""
    context = _context(
        latest_quote=QuoteValue(Decimal("-37.63")),
        previous_close=QuoteValue(Decimal("-14.00")),
        session_high=QuoteValue(Decimal("-10.50")),
        session_low=QuoteValue(Decimal("-40.32")),
        recent_closes=_series("-37.63"),
    )

    assert context.latest_quote == QuoteValue(Decimal("-37.63"))
    assert context.session_low == QuoteValue(Decimal("-40.32"))


def test_a_session_crossing_zero_is_valid() -> None:
    context = _context(
        latest_quote=QuoteValue(Decimal("0")),
        session_high=QuoteValue(Decimal("11")),
        session_low=QuoteValue(Decimal("-5.25")),
    )

    assert context.session_low.value < 0 < context.session_high.value
    assert context.latest_quote == QuoteValue(Decimal("0"))


def test_a_zero_quotation_is_valid() -> None:
    context = _context(
        latest_quote=QuoteValue(Decimal("0")),
        previous_close=QuoteValue(Decimal("0")),
        session_high=QuoteValue(Decimal("0")),
        session_low=QuoteValue(Decimal("0")),
        recent_closes=_series("0"),
    )

    assert str(context.latest_quote.value) == "0"
    assert not context.latest_quote.value.is_signed()


def test_negative_quotes_are_ordered_numerically_not_lexically() -> None:
    context = _context(
        latest_quote=QuoteValue(Decimal("-20")),
        session_high=QuoteValue(Decimal("-5.25")),
        session_low=QuoteValue(Decimal("-40.32")),
    )

    assert context.session_low < context.latest_quote < context.session_high


def test_high_precision_quotations_are_preserved() -> None:
    precise = "7660.12345678901234567890123456789012345678901234567891"
    context = _context(
        latest_quote=QuoteValue(Decimal(precise)),
        session_high=QuoteValue(Decimal("9999")),
        session_low=QuoteValue(Decimal("0")),
    )

    assert str(context.latest_quote.value) == precise


def test_no_currency_exists_anywhere_on_the_context() -> None:
    context = _context()

    for absent in ("currency", "denomination", "quote_currency"):
        assert not hasattr(context, absent)
    for quote in (context.latest_quote, context.session_high, *context.recent_closes[:3]):
        assert not hasattr(quote, "currency")


def test_a_price_is_not_accepted_as_a_quotation() -> None:
    from northstar_core.foundation.value_objects import Currency

    with pytest.raises(InvalidFuturesMarketObservationContextError, match="must be a QuoteValue"):
        _context(latest_quote=Price(Decimal("7663"), Currency("USD")))


# ---------------------------------------------------------------------------
# Context: type validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field_name", "expected"),
    [
        ("contract", "contract cannot be None"),
        ("timeframe", "timeframe cannot be None"),
        ("observed_at", "observed-at cannot be None"),
        ("latest_quote", "latest quote cannot be None"),
        ("previous_close", "previous close cannot be None"),
        ("latest_volume", "latest volume cannot be None"),
        ("session_high", "session high cannot be None"),
        ("session_low", "session low cannot be None"),
    ],
)
def test_none_members_are_rejected(field_name: str, expected: str) -> None:
    with pytest.raises(InvalidFuturesMarketObservationContextError, match=expected):
        _context(**{field_name: None})


def test_wrong_member_types_are_rejected() -> None:
    with pytest.raises(
        InvalidFuturesMarketObservationContextError, match="must be a FuturesContract"
    ):
        _context(contract=_ES)
    with pytest.raises(
        InvalidFuturesMarketObservationContextError, match="must be a Timeframe value"
    ):
        _context(timeframe="1d")
    with pytest.raises(
        InvalidFuturesMarketObservationContextError, match="must be a PointInTime value"
    ):
        _context(observed_at="2026-09-15T22:00:00Z")
    with pytest.raises(
        InvalidFuturesMarketObservationContextError, match="must be a Quantity value"
    ):
        _context(latest_volume=Decimal("100"))


def test_history_must_be_a_tuple() -> None:
    with pytest.raises(
        InvalidFuturesMarketObservationContextError, match="recent closes must be a tuple"
    ):
        _context(recent_closes=list(_series()))


def test_the_error_is_a_validation_error() -> None:
    assert issubclass(InvalidFuturesMarketObservationContextError, ValidationError)


# ---------------------------------------------------------------------------
# Context: value semantics
# ---------------------------------------------------------------------------


def test_the_context_is_immutable() -> None:
    context = _context()

    with pytest.raises(AttributeError):
        context.latest_quote = QuoteValue(Decimal("1"))


def test_equality_follows_value() -> None:
    assert _context() == _context()
    assert _context() != _context(contract=_ES_MAR)


# ---------------------------------------------------------------------------
# FuturesAssetAnalysis
# ---------------------------------------------------------------------------


def test_an_analysis_preserves_its_members() -> None:
    analysis = _analysis()

    assert analysis.contract == _ES_DEC
    assert analysis.point_in_time == _INSTANT
    assert analysis.summarized_signals == ("strong bullish",)


def test_analysis_signals_are_trimmed() -> None:
    analysis = FuturesAssetAnalysis(_ES_DEC, _INSTANT, ("  neutral trend  ",))

    assert analysis.summarized_signals == ("neutral trend",)


def test_an_empty_analysis_signal_is_rejected() -> None:
    with pytest.raises(InvalidFuturesAssetAnalysisError, match="cannot be empty"):
        FuturesAssetAnalysis(_ES_DEC, _INSTANT, ("   ",))


def test_a_non_string_analysis_signal_is_rejected() -> None:
    with pytest.raises(InvalidFuturesAssetAnalysisError, match="must be strings"):
        FuturesAssetAnalysis(_ES_DEC, _INSTANT, (1,))


def test_analysis_none_members_are_rejected() -> None:
    with pytest.raises(InvalidFuturesAssetAnalysisError, match="contract cannot be None"):
        FuturesAssetAnalysis(None, _INSTANT, ("x",))
    with pytest.raises(InvalidFuturesAssetAnalysisError, match="point-in-time"):
        FuturesAssetAnalysis(_ES_DEC, None, ("x",))
    with pytest.raises(InvalidFuturesAssetAnalysisError, match="signals cannot be None"):
        FuturesAssetAnalysis(_ES_DEC, _INSTANT, None)


def test_the_analysis_carries_no_listing_or_execution_state() -> None:
    """Analytical output, not execution state."""
    analysis = _analysis()

    for absent in (
        "listing_reference",
        "quantity",
        "multiplier",
        "margin",
        "exposure",
        "position",
        "order",
    ):
        assert not hasattr(analysis, absent)


def test_a_futures_analysis_is_not_an_equity_analysis() -> None:
    assert not isinstance(_analysis(), AssetAnalysis)
    assert not issubclass(FuturesAssetAnalysis, AssetAnalysis)


def test_the_analysis_is_immutable_and_value_typed() -> None:
    with pytest.raises(AttributeError):
        _analysis().contract = _ES_MAR
    assert _analysis() == _analysis()
    assert hash(_analysis()) == hash(_analysis())


# ---------------------------------------------------------------------------
# FuturesRecommendation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("action", ["BUY", "HOLD", "SELL"])
def test_every_directional_action_is_representable(action: str) -> None:
    recommendation = FuturesRecommendation(
        RecommendationAction(action), _analysis(), _STRATEGY, _INSTANT
    )

    assert recommendation.action == RecommendationAction(action)


def test_the_recommendation_reuses_the_existing_action_vocabulary() -> None:
    """No futures-specific enum: the three directional states already exist."""
    recommendation = _recommendation()

    assert isinstance(recommendation.action, RecommendationAction)


def test_the_recommendation_exposes_its_contract_through_the_analysis() -> None:
    recommendation = _recommendation()

    assert recommendation.contract == _ES_DEC
    assert recommendation.contract is recommendation.asset_analysis.contract


def test_recommendation_none_and_type_validation() -> None:
    with pytest.raises(InvalidFuturesRecommendationError, match="action cannot be None"):
        FuturesRecommendation(None, _analysis(), _STRATEGY, _INSTANT)
    with pytest.raises(InvalidFuturesRecommendationError, match="asset analysis cannot be None"):
        FuturesRecommendation(RecommendationAction("BUY"), None, _STRATEGY, _INSTANT)
    with pytest.raises(InvalidFuturesRecommendationError, match="must be a RecommendationAction"):
        FuturesRecommendation("BUY", _analysis(), _STRATEGY, _INSTANT)
    with pytest.raises(InvalidFuturesRecommendationError, match="strategy identity"):
        FuturesRecommendation(RecommendationAction("BUY"), _analysis(), None, _INSTANT)
    with pytest.raises(InvalidFuturesRecommendationError, match="point-in-time"):
        FuturesRecommendation(RecommendationAction("BUY"), _analysis(), _STRATEGY, None)


def test_an_equity_analysis_is_not_accepted() -> None:
    from northstar_core.domain.value_objects import ListingReference

    equity = AssetAnalysis(
        ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ")), _INSTANT, ("neutral trend",)
    )

    with pytest.raises(InvalidFuturesRecommendationError, match="must be a FuturesAssetAnalysis"):
        FuturesRecommendation(RecommendationAction("BUY"), equity, _STRATEGY, _INSTANT)


def test_the_recommendation_carries_no_execution_semantics() -> None:
    """SELL is a direction here, not an order, a short, or a position change."""
    recommendation = _recommendation()

    for absent in (
        "quantity",
        "side",
        "multiplier",
        "tick_size",
        "margin",
        "exposure",
        "position",
        "order",
        "notional",
    ):
        assert not hasattr(recommendation, absent)


def test_a_futures_recommendation_is_not_an_equity_recommendation() -> None:
    assert not isinstance(_recommendation(), Recommendation)
    assert not issubclass(FuturesRecommendation, Recommendation)


def test_the_recommendation_is_immutable_and_value_typed() -> None:
    with pytest.raises(AttributeError):
        _recommendation().action = RecommendationAction("SELL")
    assert _recommendation() == _recommendation()
    assert hash(_recommendation()) == hash(_recommendation())


def test_string_forms_name_the_contract() -> None:
    assert "ES@CME 2026-12-18" in str(_analysis())
    assert "BUY" in str(_recommendation())
    assert repr(_recommendation()).startswith("FuturesRecommendation(action=")


# ---------------------------------------------------------------------------
# Cross-contract isolation
# ---------------------------------------------------------------------------


def test_two_expiries_of_one_product_are_distinct_subjects() -> None:
    assert _context(contract=_ES_DEC) != _context(contract=_ES_MAR)
    assert _analysis(_ES_DEC) != _analysis(_ES_MAR)
    assert _recommendation(_ES_DEC) != _recommendation(_ES_MAR)


def test_standard_and_micro_products_are_distinct_subjects() -> None:
    assert _context(contract=_ES_DEC) != _context(contract=_MES_DEC)
    assert _analysis(_ES_DEC) != _analysis(_MES_DEC)
    assert _recommendation(_ES_DEC) != _recommendation(_MES_DEC)


def test_different_venues_are_distinct_subjects() -> None:
    assert _analysis(_ES_DEC) != _analysis(_CL_DEC)


def test_distinct_subjects_do_not_collapse_in_a_set() -> None:
    subjects = {
        _analysis(_ES_DEC),
        _analysis(_ES_MAR),
        _analysis(_MES_DEC),
        _analysis(_CL_DEC),
    }

    assert len(subjects) == 4


def test_a_rebuilt_equal_contract_is_accepted_by_value() -> None:
    rebuilt = FuturesContract(
        FuturesProductReference(Symbol("ES"), ExchangeCode("CME")),
        ExpirationDate("2026-12-18"),
    )

    assert rebuilt is not _ES_DEC
    assert _analysis(rebuilt) == _analysis(_ES_DEC)
    assert _context(contract=rebuilt) == _context(contract=_ES_DEC)


# ---------------------------------------------------------------------------
# Recommendation time coherence
# ---------------------------------------------------------------------------


def test_the_recommendation_instant_must_equal_its_analysis_instant() -> None:
    """A view derived from one analysis cannot be decided at another moment."""
    with pytest.raises(InvalidFuturesRecommendationError, match="must equal its analysis"):
        FuturesRecommendation(
            RecommendationAction("BUY"),
            _analysis(),
            _STRATEGY,
            PointInTime("2026-09-16T22:00:00Z"),
        )


def test_an_earlier_recommendation_instant_is_also_rejected() -> None:
    with pytest.raises(InvalidFuturesRecommendationError, match="must equal its analysis"):
        FuturesRecommendation(
            RecommendationAction("SELL"),
            _analysis(),
            _STRATEGY,
            PointInTime("2026-09-14T22:00:00Z"),
        )


def test_an_offset_equivalent_recommendation_instant_is_accepted() -> None:
    """Compared semantically: no text equality is used."""
    offset = PointInTime("2026-09-16T03:30:00+05:30")

    assert offset.compare(_INSTANT) == 0
    recommendation = FuturesRecommendation(
        RecommendationAction("HOLD"), _analysis(), _STRATEGY, offset
    )

    assert recommendation.point_in_time.compare(recommendation.asset_analysis.point_in_time) == 0


def test_a_sub_second_recommendation_instant_must_match_exactly() -> None:
    """'.5Z' sorts before 'Z' as text while being the later instant."""
    fractional = PointInTime("2026-09-15T22:00:00.5Z")

    assert fractional.value < _INSTANT.value  # the text trap
    with pytest.raises(InvalidFuturesRecommendationError, match="must equal its analysis"):
        FuturesRecommendation(RecommendationAction("BUY"), _analysis(), _STRATEGY, fractional)
