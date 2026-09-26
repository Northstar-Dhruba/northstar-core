"""Tests for the closed broker environment vocabulary."""

from __future__ import annotations

import pytest

from northstar_core.broker_execution import BrokerEnvironment


def test_vocabulary_is_exactly_demo() -> None:
    assert [environment.value for environment in BrokerEnvironment] == ["DEMO"]
    assert list(BrokerEnvironment.__members__) == ["DEMO"]


@pytest.mark.parametrize("name", ["LIVE", "PAPER", "SANDBOX", "TEST", "PRODUCTION", "REAL"])
def test_no_other_environment_is_a_member(name: str) -> None:
    """Real-money execution must not be representable at all."""
    assert not hasattr(BrokerEnvironment, name)
    assert name not in BrokerEnvironment.__members__


@pytest.mark.parametrize("value", ["LIVE", "live", "PAPER", "SANDBOX", "TEST", "", "demo"])
def test_other_values_cannot_be_constructed(value: str) -> None:
    with pytest.raises(ValueError):
        BrokerEnvironment(value)


def test_demo_is_constructible_from_its_own_value() -> None:
    assert BrokerEnvironment("DEMO") is BrokerEnvironment.DEMO
    assert str(BrokerEnvironment.DEMO) == "DEMO"
