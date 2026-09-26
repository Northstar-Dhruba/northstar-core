"""Reference contract test suite for the ParticipantIdentity value object.

This suite defines the Northstar Reference Participant Identity Value Object
contract for ParticipantIdentity.
"""

import pytest

from northstar_core.domain.value_objects import (
    InvalidParticipantIdentityError,
    ParticipantIdentity,
)
from northstar_core.foundation.exceptions.validation import ValidationError

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_participant_identity_from_opaque_identity():
    participant_identity = ParticipantIdentity("participant-opaque-001")

    assert participant_identity.identity == "participant-opaque-001"


def test_normalizes_surrounding_whitespace_from_opaque_identity():
    participant_identity = ParticipantIdentity("  participant-opaque-001  ")

    assert participant_identity.identity == "participant-opaque-001"


def test_preserves_canonical_opaque_participant_identity():
    participant_identity = ParticipantIdentity("opaque-participant-reference")

    assert str(participant_identity) == "opaque-participant-reference"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none():
    with pytest.raises(InvalidParticipantIdentityError, match="cannot be None"):
        ParticipantIdentity(None)


def test_rejects_empty_value():
    with pytest.raises(InvalidParticipantIdentityError, match="cannot be empty"):
        ParticipantIdentity("")


def test_rejects_whitespace_only_value():
    with pytest.raises(InvalidParticipantIdentityError, match="cannot be empty"):
        ParticipantIdentity("   ")


def test_rejects_incorrect_type():
    with pytest.raises(InvalidParticipantIdentityError, match="must be a string"):
        ParticipantIdentity(1)


def test_invalid_participant_identity_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        ParticipantIdentity(None)


def test_invalid_participant_identity_error_is_a_value_error():
    with pytest.raises(ValueError):
        ParticipantIdentity(None)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_surrounding_whitespace_is_removed():
    participant_identity = ParticipantIdentity("\t participant-opaque-001 \n")

    assert participant_identity.identity == "participant-opaque-001"


def test_normalization_preserves_deterministic_comparison():
    left = ParticipantIdentity("  participant-opaque-001")
    right = ParticipantIdentity("participant-opaque-001  ")

    assert left == right


def test_normalization_does_not_derive_participant_meaning():
    participant_identity = ParticipantIdentity("Orders-Trades-Portfolio-Participant")

    assert participant_identity.identity == "Orders-Trades-Portfolio-Participant"
    assert str(participant_identity) == "Orders-Trades-Portfolio-Participant"


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_participant_identity_values_compare_equal():
    assert ParticipantIdentity("participant-opaque-001") == ParticipantIdentity(
        "participant-opaque-001"
    )


def test_different_opaque_participant_identities_are_not_equal():
    assert ParticipantIdentity("participant-opaque-001") != ParticipantIdentity(
        "participant-opaque-002"
    )


def test_identity_equality_is_independent_of_business_attributes():
    left = ParticipantIdentity("opaque-left")
    right = ParticipantIdentity("opaque-right")

    assert left != right


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_participant_identity_values_have_equal_hashes():
    assert hash(ParticipantIdentity("participant-opaque-001")) == hash(
        ParticipantIdentity(" participant-opaque-001 ")
    )


def test_participant_identity_is_usable_as_dictionary_key():
    index = {ParticipantIdentity("participant-opaque-001"): "participant"}

    assert index[ParticipantIdentity("  participant-opaque-001  ")] == "participant"


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_returns_deterministic_canonical_business_representation():
    assert str(ParticipantIdentity("  participant-opaque-001  ")) == ("participant-opaque-001")


def test_repr_contains_participant_identity_and_opaque_identity():
    representation = repr(ParticipantIdentity("participant-opaque-001"))

    assert "ParticipantIdentity" in representation
    assert "participant-opaque-001" in representation
    assert "identity" in representation


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_participant_identity_is_immutable():
    participant_identity = ParticipantIdentity("participant-opaque-001")

    with pytest.raises(AttributeError):
        participant_identity.identity = "participant-opaque-002"


def test_participant_identity_does_not_support_ordering():
    left = ParticipantIdentity("participant-opaque-001")
    right = ParticipantIdentity("participant-opaque-002")

    with pytest.raises(TypeError):
        _ = left < right


def test_opaque_participant_identity_remains_uninterpreted():
    participant_identity = ParticipantIdentity("not-a-uuid-or-database-key")

    assert participant_identity.identity == "not-a-uuid-or-database-key"


def test_participant_identity_does_not_expose_business_context():
    participant_identity = ParticipantIdentity("participant-opaque-001")

    assert not hasattr(participant_identity, "participant_profile")
    assert not hasattr(participant_identity, "participant_lifecycle")
    assert not hasattr(participant_identity, "orders")
    assert not hasattr(participant_identity, "trades")
    assert not hasattr(participant_identity, "portfolio")
    assert not hasattr(participant_identity, "listing")
    assert not hasattr(participant_identity, "market_data")
