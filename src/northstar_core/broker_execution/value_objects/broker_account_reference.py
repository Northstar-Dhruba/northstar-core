"""Northstar reference to one configured broker account.

A BrokerAccountReference names which broker account an execution belongs to:
the broker Northstar knows it by, the account code within that broker, and the
environment the account lives in. It is an opaque reference, not a broker
connection: it carries no credential, token, endpoint, session or permission.

``broker_code`` and ``account_code`` follow the opaque identity convention --
surrounding whitespace is removed and the result must be non-empty -- and
nothing inside them is interpreted, case-folded or length-checked. How a broker
spells its account numbers is that broker's concern, and assuming a format here
would put broker-specific semantics into Core.

The environment is composed into the reference because an account belongs to
exactly one environment. Since BrokerEnvironment has only DEMO, a reference to a
real-money account cannot be constructed.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.broker_execution.value_objects.broker_environment import BrokerEnvironment
from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidBrokerAccountReferenceError(ValidationError):
    """Raised when a BrokerAccountReference value is invalid."""


def _normalize_code(value: str, name: str) -> str:
    if value is None:
        raise InvalidBrokerAccountReferenceError(f"BrokerAccountReference {name} cannot be None.")
    if not isinstance(value, str):
        raise InvalidBrokerAccountReferenceError(f"BrokerAccountReference {name} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise InvalidBrokerAccountReferenceError(f"BrokerAccountReference {name} cannot be empty.")
    return normalized


def _validate_environment(value: BrokerEnvironment) -> BrokerEnvironment:
    if value is None:
        raise InvalidBrokerAccountReferenceError(
            "BrokerAccountReference environment cannot be None."
        )
    if not isinstance(value, BrokerEnvironment):
        raise InvalidBrokerAccountReferenceError(
            "BrokerAccountReference environment must be a BrokerEnvironment value."
        )
    return value


@dataclass(frozen=True, slots=True)
class BrokerAccountReference:
    """Immutable opaque reference to one broker account in one environment."""

    broker_code: str
    account_code: str
    environment: BrokerEnvironment

    def __post_init__(self) -> None:
        object.__setattr__(self, "broker_code", _normalize_code(self.broker_code, "broker code"))
        object.__setattr__(self, "account_code", _normalize_code(self.account_code, "account code"))
        object.__setattr__(self, "environment", _validate_environment(self.environment))

    def __str__(self) -> str:
        return f"{self.broker_code}/{self.account_code} {self.environment}"

    def __repr__(self) -> str:
        return (
            "BrokerAccountReference("
            f"broker_code={self.broker_code!r}, "
            f"account_code={self.account_code!r}, "
            f"environment={self.environment!r}"
            ")"
        )
