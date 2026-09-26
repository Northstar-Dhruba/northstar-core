"""Tests for the paper-trading opaque identity value objects.

The three identities are structurally identical by design -- they follow the
same convention as StrategyIdentity -- so they are verified together against
one shared contract rather than in three duplicated files.
"""

from __future__ import annotations

import pytest

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.paper_trading import (
    InvalidPaperFillIdentityError,
    InvalidPaperOrderIdentityError,
    InvalidPaperPortfolioIdentityError,
    PaperFillIdentity,
    PaperOrderIdentity,
    PaperPortfolioIdentity,
)

_IDENTITIES = [
    pytest.param(PaperPortfolioIdentity, InvalidPaperPortfolioIdentityError, id="portfolio"),
    pytest.param(PaperOrderIdentity, InvalidPaperOrderIdentityError, id="order"),
    pytest.param(PaperFillIdentity, InvalidPaperFillIdentityError, id="fill"),
]


@pytest.mark.parametrize(("identity_type", "error"), _IDENTITIES)
def test_identity_preserves_its_value(identity_type: type, error: type) -> None:
    assert identity_type("abc-123").identity == "abc-123"


@pytest.mark.parametrize(("identity_type", "error"), _IDENTITIES)
def test_surrounding_whitespace_is_normalized(identity_type: type, error: type) -> None:
    assert identity_type("  abc-123  ").identity == "abc-123"
    assert identity_type("\tabc\n").identity == "abc"


@pytest.mark.parametrize(("identity_type", "error"), _IDENTITIES)
def test_interior_characters_are_preserved(identity_type: type, error: type) -> None:
    """Identity format is intentionally undefined, so nothing inside is altered."""
    assert identity_type("a b/C-1_2").identity == "a b/C-1_2"


@pytest.mark.parametrize(("identity_type", "error"), _IDENTITIES)
def test_none_is_rejected(identity_type: type, error: type) -> None:
    with pytest.raises(error, match="cannot be None"):
        identity_type(None)


@pytest.mark.parametrize(("identity_type", "error"), _IDENTITIES)
@pytest.mark.parametrize("value", [1, 1.0, True, b"abc", ["abc"], {"a": 1}, object()])
def test_non_string_values_are_rejected(identity_type: type, error: type, value: object) -> None:
    with pytest.raises(error, match="must be a string"):
        identity_type(value)


@pytest.mark.parametrize(("identity_type", "error"), _IDENTITIES)
@pytest.mark.parametrize("value", ["", "   ", "\t", "\n", " \t\n "])
def test_empty_and_blank_values_are_rejected(identity_type: type, error: type, value: str) -> None:
    with pytest.raises(error, match="cannot be empty"):
        identity_type(value)


@pytest.mark.parametrize(("identity_type", "error"), _IDENTITIES)
def test_errors_are_validation_errors(identity_type: type, error: type) -> None:
    assert issubclass(error, ValidationError)
    with pytest.raises(ValidationError):
        identity_type("")


@pytest.mark.parametrize(("identity_type", "error"), _IDENTITIES)
def test_equality_is_by_value_after_normalization(identity_type: type, error: type) -> None:
    assert identity_type("abc") == identity_type("  abc  ")
    assert identity_type("abc") != identity_type("abd")


@pytest.mark.parametrize(("identity_type", "error"), _IDENTITIES)
def test_hashing_follows_equality(identity_type: type, error: type) -> None:
    assert hash(identity_type("abc")) == hash(identity_type(" abc "))
    assert len({identity_type("abc"), identity_type("abc"), identity_type("abd")}) == 2


@pytest.mark.parametrize(("identity_type", "error"), _IDENTITIES)
def test_identity_is_immutable(identity_type: type, error: type) -> None:
    identity = identity_type("abc")
    with pytest.raises(AttributeError):
        identity.identity = "changed"


@pytest.mark.parametrize(("identity_type", "error"), _IDENTITIES)
def test_string_and_repr_forms(identity_type: type, error: type) -> None:
    identity = identity_type("abc")
    assert str(identity) == "abc"
    assert repr(identity) == f"{identity_type.__name__}(identity='abc')"


def test_identity_types_do_not_compare_equal_to_each_other() -> None:
    """Distinct identity kinds must never be interchangeable, even at one value."""
    assert PaperOrderIdentity("x") != PaperFillIdentity("x")
    assert PaperFillIdentity("x") != PaperPortfolioIdentity("x")
    assert PaperPortfolioIdentity("x") != PaperOrderIdentity("x")
