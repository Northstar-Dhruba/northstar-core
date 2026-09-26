"""Contract test suite for the ResearchHorizon value object."""

from decimal import Decimal

import pytest

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.strategy import InvalidResearchHorizonError, ResearchHorizon

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_horizon_from_positive_observation_count() -> None:
    horizon = ResearchHorizon(5)

    assert horizon.observations == 5


def test_smallest_valid_horizon_is_one_observation() -> None:
    assert ResearchHorizon(1).observations == 1


def test_supports_keyword_construction() -> None:
    assert ResearchHorizon(observations=20).observations == 20


@pytest.mark.parametrize("observations", [1, 5, 20, 250])
def test_accepts_representative_research_horizons(observations: int) -> None:
    assert ResearchHorizon(observations).observations == observations


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_zero_observations() -> None:
    with pytest.raises(InvalidResearchHorizonError, match="at least one observation"):
        ResearchHorizon(0)


@pytest.mark.parametrize("observations", [-1, -5, -20])
def test_rejects_negative_observations(observations: int) -> None:
    with pytest.raises(InvalidResearchHorizonError, match="at least one observation"):
        ResearchHorizon(observations)


def test_rejects_none() -> None:
    with pytest.raises(InvalidResearchHorizonError, match="cannot be None"):
        ResearchHorizon(None)


@pytest.mark.parametrize("observations", [True, False])
def test_rejects_bool(observations: bool) -> None:
    with pytest.raises(InvalidResearchHorizonError, match="must be an integer"):
        ResearchHorizon(observations)


@pytest.mark.parametrize("observations", ["5", 5.0, Decimal("5"), (5,), [5]])
def test_rejects_non_integer_types(observations: object) -> None:
    with pytest.raises(InvalidResearchHorizonError, match="must be an integer"):
        ResearchHorizon(observations)


def test_invalid_research_horizon_error_is_a_validation_error() -> None:
    with pytest.raises(ValidationError):
        ResearchHorizon(0)


def test_invalid_research_horizon_error_is_a_value_error() -> None:
    with pytest.raises(ValueError):
        ResearchHorizon(0)


# ---------------------------------------------------------------------------
# Semantics
# ---------------------------------------------------------------------------


def test_horizon_carries_no_calendar_or_timeframe_meaning() -> None:
    horizon = ResearchHorizon(5)

    assert not hasattr(horizon, "timeframe")
    assert not hasattr(horizon, "duration")
    assert not hasattr(horizon, "days")
    assert not hasattr(horizon, "calendar")


def test_horizon_exposes_exactly_the_observation_count() -> None:
    assert ResearchHorizon.__slots__ == ("observations",)
    assert not hasattr(ResearchHorizon(5), "__dict__")


# ---------------------------------------------------------------------------
# Equality, ordering and hashing
# ---------------------------------------------------------------------------


def test_equal_horizons_compare_equal() -> None:
    assert ResearchHorizon(5) == ResearchHorizon(5)


def test_different_horizons_do_not_compare_equal() -> None:
    assert ResearchHorizon(5) != ResearchHorizon(20)


def test_horizon_does_not_compare_equal_to_plain_integer() -> None:
    assert ResearchHorizon(5) != 5


def test_horizons_are_orderable() -> None:
    assert ResearchHorizon(1) < ResearchHorizon(5) < ResearchHorizon(20)
    assert sorted([ResearchHorizon(20), ResearchHorizon(1), ResearchHorizon(5)]) == [
        ResearchHorizon(1),
        ResearchHorizon(5),
        ResearchHorizon(20),
    ]


def test_equal_horizons_have_equal_hashes() -> None:
    assert hash(ResearchHorizon(5)) == hash(ResearchHorizon(5))


def test_horizon_is_usable_as_dictionary_key() -> None:
    index = {ResearchHorizon(1): "next", ResearchHorizon(20): "month"}

    assert index[ResearchHorizon(1)] == "next"
    assert index[ResearchHorizon(20)] == "month"


# ---------------------------------------------------------------------------
# Representation and immutability
# ---------------------------------------------------------------------------


def test_str_renders_the_observation_count() -> None:
    assert str(ResearchHorizon(5)) == "5"


def test_repr_contains_research_horizon_and_observations() -> None:
    representation = repr(ResearchHorizon(5))

    assert "ResearchHorizon" in representation
    assert "observations=5" in representation


def test_horizon_is_immutable() -> None:
    horizon = ResearchHorizon(5)

    with pytest.raises(AttributeError):
        horizon.observations = 20
