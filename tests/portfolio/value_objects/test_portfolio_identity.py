"""Reference contract test suite for the PortfolioIdentity value object.

This suite defines the Northstar Reference Aggregate Identity Value Object
contract for PortfolioIdentity.
"""

import pytest

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.portfolio.value_objects import (
    InvalidPortfolioIdentityError,
    PortfolioIdentity,
)

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_portfolio_identity_from_opaque_identity():
    portfolio_identity = PortfolioIdentity("portfolio-opaque-001")

    assert portfolio_identity.identity == "portfolio-opaque-001"


def test_normalizes_surrounding_whitespace_from_opaque_identity():
    portfolio_identity = PortfolioIdentity("  portfolio-opaque-001  ")

    assert portfolio_identity.identity == "portfolio-opaque-001"


def test_preserves_canonical_opaque_portfolio_identity():
    portfolio_identity = PortfolioIdentity("opaque-portfolio-reference")

    assert str(portfolio_identity) == "opaque-portfolio-reference"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none():
    with pytest.raises(InvalidPortfolioIdentityError, match="cannot be None"):
        PortfolioIdentity(None)


def test_rejects_empty_value():
    with pytest.raises(InvalidPortfolioIdentityError, match="cannot be empty"):
        PortfolioIdentity("")


def test_rejects_whitespace_only_value():
    with pytest.raises(InvalidPortfolioIdentityError, match="cannot be empty"):
        PortfolioIdentity("   ")


def test_rejects_incorrect_type():
    with pytest.raises(InvalidPortfolioIdentityError, match="must be a string"):
        PortfolioIdentity(1)


def test_invalid_portfolio_identity_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        PortfolioIdentity(None)


def test_invalid_portfolio_identity_error_is_a_value_error():
    with pytest.raises(ValueError):
        PortfolioIdentity(None)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_surrounding_whitespace_is_removed():
    portfolio_identity = PortfolioIdentity("\t portfolio-opaque-001 \n")

    assert portfolio_identity.identity == "portfolio-opaque-001"


def test_normalization_preserves_deterministic_comparison():
    left = PortfolioIdentity("  portfolio-opaque-001")
    right = PortfolioIdentity("portfolio-opaque-001  ")

    assert left == right


def test_normalization_does_not_derive_business_meaning():
    portfolio_identity = PortfolioIdentity("Position-Participant-Trade-Risk-Performance")

    assert portfolio_identity.identity == "Position-Participant-Trade-Risk-Performance"
    assert str(portfolio_identity) == "Position-Participant-Trade-Risk-Performance"


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_portfolio_identity_values_compare_equal():
    assert PortfolioIdentity("portfolio-opaque-001") == PortfolioIdentity("portfolio-opaque-001")


def test_different_opaque_portfolio_identities_are_not_equal():
    assert PortfolioIdentity("portfolio-opaque-001") != PortfolioIdentity("portfolio-opaque-002")


def test_identity_equality_is_independent_of_business_attributes():
    assert PortfolioIdentity("opaque-left") != PortfolioIdentity("opaque-right")


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_portfolio_identity_values_have_equal_hashes():
    assert hash(PortfolioIdentity("portfolio-opaque-001")) == hash(
        PortfolioIdentity(" portfolio-opaque-001 ")
    )


def test_portfolio_identity_is_usable_as_dictionary_key():
    index = {PortfolioIdentity("portfolio-opaque-001"): "portfolio"}

    assert index[PortfolioIdentity("  portfolio-opaque-001  ")] == "portfolio"


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_deterministic_canonical_business_representation():
    assert str(PortfolioIdentity("  portfolio-opaque-001  ")) == "portfolio-opaque-001"


def test_repr_contains_portfolio_identity_and_opaque_identity():
    representation = repr(PortfolioIdentity("portfolio-opaque-001"))

    assert "PortfolioIdentity" in representation
    assert "portfolio-opaque-001" in representation
    assert "identity" in representation


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_portfolio_identity_is_immutable():
    portfolio_identity = PortfolioIdentity("portfolio-opaque-001")

    with pytest.raises(AttributeError):
        portfolio_identity.identity = "portfolio-opaque-002"


def test_portfolio_identity_does_not_support_ordering():
    with pytest.raises(TypeError):
        _ = PortfolioIdentity("portfolio-opaque-001") < PortfolioIdentity("portfolio-opaque-002")


def test_opaque_portfolio_identity_remains_uninterpreted():
    portfolio_identity = PortfolioIdentity("not-a-uuid-or-database-key")

    assert portfolio_identity.identity == "not-a-uuid-or-database-key"


def test_portfolio_identity_does_not_expose_business_context():
    portfolio_identity = PortfolioIdentity("portfolio-opaque-001")

    assert not hasattr(portfolio_identity, "position")
    assert not hasattr(portfolio_identity, "participant")
    assert not hasattr(portfolio_identity, "participant_reference")
    assert not hasattr(portfolio_identity, "trade")
    assert not hasattr(portfolio_identity, "market_data")
    assert not hasattr(portfolio_identity, "risk")
    assert not hasattr(portfolio_identity, "performance")
    assert not hasattr(portfolio_identity, "portfolio_state")
