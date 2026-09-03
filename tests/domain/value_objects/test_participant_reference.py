"""Reference contract test suite for the ParticipantReference value object.

This suite defines the Northstar Reference Identity Association Value Object
contract for ParticipantReference.
"""

import pytest

from northstar_core.domain.value_objects import (
    InvalidParticipantReferenceError,
    ParticipantIdentity,
    ParticipantReference,
)
from northstar_core.foundation.exceptions.validation import ValidationError

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_creates_valid_participant_reference_from_participant_identity():
    participant_identity = ParticipantIdentity("participant-opaque-001")
    reference = ParticipantReference(participant_identity)

    assert reference.participant_identity is participant_identity


def test_preserves_canonical_participant_identity_composition():
    reference = ParticipantReference(ParticipantIdentity("participant-opaque-001"))

    assert reference.participant_identity == ParticipantIdentity("participant-opaque-001")


def test_constructs_deterministically_from_equivalent_participant_identity():
    left = ParticipantReference(ParticipantIdentity("participant-opaque-001"))
    right = ParticipantReference(ParticipantIdentity(" participant-opaque-001 "))

    assert left == right


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_none():
    with pytest.raises(InvalidParticipantReferenceError, match="cannot be None"):
        ParticipantReference(None)


def test_rejects_invalid_type():
    with pytest.raises(InvalidParticipantReferenceError, match="must be a ParticipantIdentity"):
        ParticipantReference("participant-opaque-001")


def test_invalid_participant_reference_error_is_a_validation_error():
    with pytest.raises(ValidationError):
        ParticipantReference(None)


def test_invalid_participant_reference_error_is_a_value_error():
    with pytest.raises(ValueError):
        ParticipantReference(None)


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def test_participant_reference_composes_exactly_one_participant_identity():
    participant_identity = ParticipantIdentity("participant-opaque-001")
    reference = ParticipantReference(participant_identity)

    assert isinstance(reference.participant_identity, ParticipantIdentity)
    assert reference.participant_identity is participant_identity


def test_participant_identity_remains_authoritative_owner_of_identity_meaning():
    participant_identity = ParticipantIdentity("participant-opaque-001")
    reference = ParticipantReference(participant_identity)

    assert reference.participant_identity.identity == participant_identity.identity
    assert not hasattr(reference, "participant")


def test_participant_reference_does_not_compose_consuming_business_concepts():
    reference = ParticipantReference(ParticipantIdentity("participant-opaque-001"))

    assert not hasattr(reference, "orders")
    assert not hasattr(reference, "trades")
    assert not hasattr(reference, "portfolio")
    assert not hasattr(reference, "listing")
    assert not hasattr(reference, "market_data")


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_participant_reference_delegates_identity_normalization():
    reference = ParticipantReference(ParticipantIdentity("  participant-opaque-001  "))

    assert reference.participant_identity.identity == "participant-opaque-001"


def test_participant_reference_does_not_redefine_identity_normalization():
    left = ParticipantReference(ParticipantIdentity("  participant-opaque-001  "))
    right = ParticipantReference(ParticipantIdentity("participant-opaque-001"))

    assert left == right
    assert left.participant_identity == right.participant_identity


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------


def test_equal_participant_references_compare_equal():
    assert ParticipantReference(ParticipantIdentity("participant-opaque-001")) == (
        ParticipantReference(ParticipantIdentity("participant-opaque-001"))
    )


def test_different_participant_identities_do_not_compare_equal():
    assert ParticipantReference(ParticipantIdentity("participant-opaque-001")) != (
        ParticipantReference(ParticipantIdentity("participant-opaque-002"))
    )


def test_participant_reference_equality_is_based_on_identity_association():
    left = ParticipantReference(ParticipantIdentity("participant-opaque-001"))
    right = ParticipantReference(ParticipantIdentity("participant-opaque-001"))

    assert left == right


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_equal_participant_references_have_equal_hashes():
    assert hash(ParticipantReference(ParticipantIdentity("participant-opaque-001"))) == hash(
        ParticipantReference(ParticipantIdentity(" participant-opaque-001 "))
    )


def test_participant_reference_is_usable_as_dictionary_key():
    index = {ParticipantReference(ParticipantIdentity("participant-opaque-001")): "participant"}

    assert index[ParticipantReference(ParticipantIdentity("participant-opaque-001"))] == (
        "participant"
    )


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_delegates_to_composed_participant_identity_representation():
    reference = ParticipantReference(ParticipantIdentity("participant-opaque-001"))

    assert str(reference) == str(reference.participant_identity)


def test_repr_contains_participant_reference_and_participant_identity():
    representation = repr(ParticipantReference(ParticipantIdentity("participant-opaque-001")))

    assert "ParticipantReference" in representation
    assert "ParticipantIdentity" in representation
    assert "participant-opaque-001" in representation


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


def test_participant_reference_is_immutable():
    reference = ParticipantReference(ParticipantIdentity("participant-opaque-001"))

    with pytest.raises(AttributeError):
        reference.participant_identity = ParticipantIdentity("participant-opaque-002")


def test_participant_reference_does_not_support_ordering():
    left = ParticipantReference(ParticipantIdentity("participant-opaque-001"))
    right = ParticipantReference(ParticipantIdentity("participant-opaque-002"))

    with pytest.raises(TypeError):
        _ = left < right


def test_identity_association_is_preserved():
    participant_identity = ParticipantIdentity("participant-opaque-001")
    reference = ParticipantReference(participant_identity)

    assert reference.participant_identity is participant_identity


def test_participant_reference_does_not_introduce_business_interpretation():
    reference = ParticipantReference(ParticipantIdentity("participant-opaque-001"))

    assert not hasattr(reference, "participant_profile")
    assert not hasattr(reference, "participant_lifecycle")
    assert not hasattr(reference, "authentication")
    assert not hasattr(reference, "authorization")
    assert not hasattr(reference, "account")
    assert not hasattr(reference, "workflow")
