"""Tests for the opaque reference to one broker account."""

from __future__ import annotations

from dataclasses import fields

import pytest

from northstar_core.broker_execution import (
    BrokerAccountReference,
    BrokerEnvironment,
    InvalidBrokerAccountReferenceError,
)
from northstar_core.foundation.exceptions.validation import ValidationError


def _account(**overrides: object) -> BrokerAccountReference:
    values: dict[str, object] = {
        "broker_code": "broker-a",
        "account_code": "DU123",
        "environment": BrokerEnvironment.DEMO,
    }
    values.update(overrides)
    return BrokerAccountReference(**values)


def test_reference_preserves_every_member() -> None:
    account = _account()

    assert account.broker_code == "broker-a"
    assert account.account_code == "DU123"
    assert account.environment is BrokerEnvironment.DEMO


def test_the_field_shape_carries_no_credential() -> None:
    assert [field.name for field in fields(BrokerAccountReference)] == [
        "broker_code",
        "account_code",
        "environment",
    ]


def test_surrounding_whitespace_is_normalized() -> None:
    account = _account(broker_code="  broker-a\t", account_code="\nDU123 ")

    assert account.broker_code == "broker-a"
    assert account.account_code == "DU123"


def test_interior_characters_and_case_are_preserved() -> None:
    """The codes are opaque: nothing inside them is interpreted or case-folded."""
    account = _account(broker_code="Broker A/1", account_code="du 123-x")

    assert account.broker_code == "Broker A/1"
    assert account.account_code == "du 123-x"
    assert _account(account_code="du123") != _account(account_code="DU123")


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("broker_code", "broker code cannot be None"),
        ("account_code", "account code cannot be None"),
        ("environment", "environment cannot be None"),
    ],
)
def test_none_members_are_rejected(field: str, message: str) -> None:
    with pytest.raises(InvalidBrokerAccountReferenceError, match=message):
        _account(**{field: None})


@pytest.mark.parametrize("field", ["broker_code", "account_code"])
@pytest.mark.parametrize("value", ["", "   ", "\t", " \t\n "])
def test_blank_codes_are_rejected(field: str, value: str) -> None:
    with pytest.raises(InvalidBrokerAccountReferenceError, match="cannot be empty"):
        _account(**{field: value})


@pytest.mark.parametrize("field", ["broker_code", "account_code"])
@pytest.mark.parametrize("value", [1, True, b"abc", ["abc"], object()])
def test_non_string_codes_are_rejected(field: str, value: object) -> None:
    with pytest.raises(InvalidBrokerAccountReferenceError, match="must be a string"):
        _account(**{field: value})


@pytest.mark.parametrize("value", ["DEMO", "LIVE", 1, object()])
def test_environment_must_be_a_broker_environment(value: object) -> None:
    """A plain string is not the closed vocabulary, even when it spells DEMO."""
    with pytest.raises(InvalidBrokerAccountReferenceError, match="must be a BrokerEnvironment"):
        _account(environment=value)


def test_error_is_a_validation_error() -> None:
    assert issubclass(InvalidBrokerAccountReferenceError, ValidationError)


def test_reference_is_immutable() -> None:
    account = _account()

    with pytest.raises(AttributeError):
        account.account_code = "other"  # type: ignore[misc]


def test_equivalent_references_compare_and_hash_equal() -> None:
    assert _account() == _account(broker_code=" broker-a ")
    assert hash(_account()) == hash(_account(account_code=" DU123 "))
    assert len({_account(), _account(), _account(account_code="DU124")}) == 2


@pytest.mark.parametrize(("field", "value"), [("broker_code", "b"), ("account_code", "DU999")])
def test_references_differing_in_any_member_are_not_equal(field: str, value: str) -> None:
    assert _account() != _account(**{field: value})


def test_string_and_repr_forms() -> None:
    account = _account()

    assert str(account) == "broker-a/DU123 DEMO"
    assert repr(account) == (
        "BrokerAccountReference(broker_code='broker-a', account_code='DU123', "
        "environment=<BrokerEnvironment.DEMO: 'DEMO'>)"
    )
