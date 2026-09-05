"""Reference contract test suite for the Portfolio aggregate root.

This suite defines the Northstar Reference Portfolio Aggregate Contract.
"""

import pytest

from northstar_core.domain.exchange import Exchange
from northstar_core.domain.instrument import Instrument
from northstar_core.domain.listing import Listing
from northstar_core.domain.value_objects import (
    ListingStatus,
    ParticipantIdentity,
    ParticipantReference,
    Tradability,
)
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency, ExchangeCode, PointInTime, Symbol
from northstar_core.portfolio import (
    InvalidPortfolioError,
    Portfolio,
    PortfolioIdentity,
    Position,
)


def _build_listing(symbol: str = "AAPL") -> Listing:
    return Listing(
        Instrument(Symbol(symbol), f"{symbol} Inc.", "Equity"),
        Exchange(ExchangeCode("NASDAQ"), "NASDAQ"),
        Currency("USD"),
        ListingStatus("Active"),
        Tradability("Permitted"),
    )


def _build_identity(value: str = "portfolio-opaque-001") -> PortfolioIdentity:
    return PortfolioIdentity(value)


def _build_participant_reference(value: str = "participant-opaque-001") -> ParticipantReference:
    return ParticipantReference(ParticipantIdentity(value))


def _build_point_in_time(value: str = "2026-08-17T09:30:00Z") -> PointInTime:
    return PointInTime(value)


def _build_position(symbol: str = "AAPL") -> Position:
    return Position(_build_listing(symbol))


def _build_portfolio(
    *,
    identity: PortfolioIdentity | None = None,
    participant_reference: ParticipantReference | None = None,
    point_in_time: PointInTime | None = None,
    positions: tuple[Position, ...] = (),
) -> Portfolio:
    return Portfolio(
        identity or _build_identity(),
        participant_reference or _build_participant_reference(),
        point_in_time or _build_point_in_time(),
        positions,
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_empty_portfolio():
    portfolio = _build_portfolio()

    assert isinstance(portfolio, Portfolio)
    assert portfolio.positions == ()


def test_creates_valid_populated_portfolio():
    position = _build_position()
    portfolio = _build_portfolio(positions=(position,))

    assert portfolio.positions == (position,)


def test_construction_preserves_approved_aggregate_composition():
    identity = _build_identity()
    participant_reference = _build_participant_reference()
    point_in_time = _build_point_in_time()
    position = _build_position()

    portfolio = Portfolio(identity, participant_reference, point_in_time, (position,))

    assert portfolio.portfolio_identity is identity
    assert portfolio.participant_reference is participant_reference
    assert portfolio.point_in_time is point_in_time
    assert portfolio.positions == (position,)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none_portfolio_identity():
    with pytest.raises(InvalidPortfolioError, match="identity cannot be None"):
        Portfolio(None, _build_participant_reference(), _build_point_in_time(), ())


def test_rejects_none_participant_reference():
    with pytest.raises(InvalidPortfolioError, match="participant reference cannot be None"):
        Portfolio(_build_identity(), None, _build_point_in_time(), ())


def test_rejects_none_point_in_time():
    with pytest.raises(InvalidPortfolioError, match="point-in-time context cannot be None"):
        Portfolio(_build_identity(), _build_participant_reference(), None, ())


def test_rejects_none_positions():
    with pytest.raises(InvalidPortfolioError, match="positions cannot be None"):
        Portfolio(_build_identity(), _build_participant_reference(), _build_point_in_time(), None)


def test_rejects_invalid_portfolio_identity_type():
    with pytest.raises(InvalidPortfolioError, match="identity must be a PortfolioIdentity"):
        Portfolio("identity", _build_participant_reference(), _build_point_in_time(), ())


def test_rejects_invalid_participant_reference_type():
    with pytest.raises(
        InvalidPortfolioError, match="participant reference must be a ParticipantReference"
    ):
        Portfolio(_build_identity(), "participant", _build_point_in_time(), ())


def test_rejects_invalid_point_in_time_type():
    with pytest.raises(InvalidPortfolioError, match="point-in-time context must be a PointInTime"):
        Portfolio(_build_identity(), _build_participant_reference(), "time", ())


def test_rejects_invalid_positions_collection_type():
    with pytest.raises(InvalidPortfolioError, match="positions must be a tuple"):
        Portfolio(_build_identity(), _build_participant_reference(), _build_point_in_time(), [])


def test_rejects_invalid_position_member_type():
    with pytest.raises(InvalidPortfolioError, match="must contain Position entities"):
        Portfolio(
            _build_identity(), _build_participant_reference(), _build_point_in_time(), ("position",)
        )


def test_invalid_portfolio_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        Portfolio(None, _build_participant_reference(), _build_point_in_time(), ())


def test_invalid_portfolio_error_is_a_value_error():
    with pytest.raises(ValueError):
        Portfolio(None, _build_participant_reference(), _build_point_in_time(), ())


# ---------------------------------------------------------------------------
# Aggregate Composition
# ---------------------------------------------------------------------------


def test_portfolio_composes_only_approved_dependencies():
    portfolio = _build_portfolio(positions=(_build_position(),))

    assert isinstance(portfolio.portfolio_identity, PortfolioIdentity)
    assert isinstance(portfolio.participant_reference, ParticipantReference)
    assert isinstance(portfolio.point_in_time, PointInTime)
    assert all(isinstance(position, Position) for position in portfolio.positions)


def test_portfolio_does_not_compose_external_business_contexts():
    portfolio = _build_portfolio()

    assert not hasattr(portfolio, "trade")
    assert not hasattr(portfolio, "order")
    assert not hasattr(portfolio, "quote")
    assert not hasattr(portfolio, "tick")
    assert not hasattr(portfolio, "ohlc_bar")
    assert not hasattr(portfolio, "order_book")
    assert not hasattr(portfolio, "risk")
    assert not hasattr(portfolio, "performance")
    assert not hasattr(portfolio, "settlement")
    assert not hasattr(portfolio, "workflow")


def test_positions_remain_subordinate_entities():
    position = _build_position()
    portfolio = _build_portfolio(positions=(position,))

    assert portfolio.positions[0] is position
    assert not hasattr(position, "portfolio")
    assert not hasattr(position, "participant_reference")
    assert not hasattr(position, "point_in_time")


# ---------------------------------------------------------------------------
# Identity Semantics
# ---------------------------------------------------------------------------


def test_portfolios_with_same_identity_compare_equal_despite_different_composition():
    left = _build_portfolio(
        identity=_build_identity("portfolio-opaque-001"),
        participant_reference=_build_participant_reference("participant-001"),
        point_in_time=_build_point_in_time("2026-08-17T09:30:00Z"),
        positions=(_build_position("AAPL"),),
    )
    right = _build_portfolio(
        identity=_build_identity(" portfolio-opaque-001 "),
        participant_reference=_build_participant_reference("participant-002"),
        point_in_time=_build_point_in_time("2026-08-17T14:30:00+05:00"),
        positions=(_build_position("MSFT"),),
    )

    assert left == right


def test_portfolios_with_different_identity_do_not_compare_equal():
    left = _build_portfolio(identity=_build_identity("portfolio-opaque-001"))
    right = _build_portfolio(identity=_build_identity("portfolio-opaque-002"))

    assert left != right


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_portfolios_have_equal_hashes():
    left = _build_portfolio(identity=_build_identity("portfolio-opaque-001"))
    right = _build_portfolio(identity=_build_identity(" portfolio-opaque-001 "))

    assert hash(left) == hash(right)


def test_portfolio_is_usable_as_dictionary_key():
    key = _build_portfolio(identity=_build_identity("portfolio-opaque-001"))
    index = {key: "ownership"}
    probe = _build_portfolio(identity=_build_identity("portfolio-opaque-001"))

    assert index[probe] == "ownership"


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_repr_contains_portfolio_and_approved_components():
    representation = repr(_build_portfolio())

    assert "Portfolio(" in representation
    assert "PortfolioIdentity(" in representation
    assert "ParticipantReference(" in representation


def test_str_returns_deterministic_business_representation():
    portfolio = _build_portfolio()

    assert str(portfolio) == str(_build_portfolio())
    assert "portfolio-opaque-001" in str(portfolio)
    assert "participant-opaque-001" in str(portfolio)


# ---------------------------------------------------------------------------
# Aggregate Consistency
# ---------------------------------------------------------------------------


def test_zero_positions_is_valid():
    assert _build_portfolio().positions == ()


def test_duplicate_listing_positions_are_rejected():
    position = _build_position()

    with pytest.raises(InvalidPortfolioError, match="multiple Positions for the same Listing"):
        Portfolio(
            _build_identity(),
            _build_participant_reference(),
            _build_point_in_time(),
            (position, Position(position.listing)),
        )


def test_one_position_per_listing_invariant_is_enforced():
    listing = _build_listing("AAPL")

    with pytest.raises(InvalidPortfolioError, match="same Listing"):
        Portfolio(
            _build_identity(),
            _build_participant_reference(),
            _build_point_in_time(),
            (Position(listing), Position(listing)),
        )


def test_position_collection_contains_only_position_entities():
    with pytest.raises(InvalidPortfolioError, match="Position entities"):
        Portfolio(
            _build_identity(),
            _build_participant_reference(),
            _build_point_in_time(),
            (_build_position(), object()),
        )


# ---------------------------------------------------------------------------
# Mutability
# ---------------------------------------------------------------------------


def test_portfolio_is_mutable():
    portfolio = _build_portfolio()
    position = _build_position()

    portfolio.positions = (position,)

    assert portfolio.positions == (position,)


def test_position_collection_may_be_replaced():
    portfolio = _build_portfolio(positions=(_build_position("AAPL"),))
    replacement = (_build_position("MSFT"),)

    portfolio.positions = replacement

    assert portfolio.positions == replacement


def test_portfolio_identity_remains_authoritative():
    identity = _build_identity()
    portfolio = _build_portfolio(identity=identity)

    portfolio.positions = (_build_position(),)

    assert portfolio.portfolio_identity is identity
    assert portfolio == _build_portfolio(identity=_build_identity(identity.identity))


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_portfolio_does_not_support_ordering():
    with pytest.raises(TypeError):
        _ = _build_portfolio() < _build_portfolio(identity=_build_identity("portfolio-002"))


def test_position_identity_remains_absent():
    portfolio = _build_portfolio(positions=(_build_position(),))

    assert not hasattr(portfolio.positions[0], "position_identity")


def test_aggregate_boundary_remains_intact():
    portfolio = _build_portfolio(positions=(_build_position(),))

    assert portfolio.positions[0] in portfolio.positions
    assert not hasattr(portfolio, "trade")
    assert not hasattr(portfolio, "order")
    assert not hasattr(portfolio, "market_data")
