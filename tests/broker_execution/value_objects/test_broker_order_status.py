"""Tests for the broker-normalized order status vocabulary."""

from __future__ import annotations

import pytest

from northstar_core.broker_execution import BrokerOrderStatus


def test_vocabulary_is_exactly_the_four_broker_statuses() -> None:
    assert [status.value for status in BrokerOrderStatus] == [
        "WORKING",
        "FILLED",
        "CANCELLED",
        "REJECTED",
    ]


@pytest.mark.parametrize(
    "name",
    ["CREATED", "SUBMITTED", "ACKNOWLEDGED", "PARTIALLY_FILLED", "PENDING", "EXPIRED", "OPEN"],
)
def test_journal_and_derived_states_are_not_members(name: str) -> None:
    """Submission is Northstar journal state; a partial fill is a filled count."""
    assert not hasattr(BrokerOrderStatus, name)
    assert name not in BrokerOrderStatus.__members__
    with pytest.raises(ValueError):
        BrokerOrderStatus(name)


@pytest.mark.parametrize(
    ("status", "terminal"),
    [
        (BrokerOrderStatus.WORKING, False),
        (BrokerOrderStatus.FILLED, True),
        (BrokerOrderStatus.CANCELLED, True),
        (BrokerOrderStatus.REJECTED, True),
    ],
)
def test_is_terminal(status: BrokerOrderStatus, terminal: bool) -> None:
    assert status.is_terminal is terminal


def test_lowercase_is_not_silently_accepted() -> None:
    with pytest.raises(ValueError):
        BrokerOrderStatus("filled")


def test_members_are_constructible_from_their_own_value() -> None:
    for status in BrokerOrderStatus:
        assert BrokerOrderStatus(status.value) is status
