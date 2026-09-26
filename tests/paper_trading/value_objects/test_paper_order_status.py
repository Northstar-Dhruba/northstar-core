"""Tests for the paper-trading order result vocabulary."""

from __future__ import annotations

import pytest

from northstar_core.paper_trading import PaperOrderStatus


def test_vocabulary_is_exactly_filled_and_rejected() -> None:
    assert [status.value for status in PaperOrderStatus] == ["FILLED", "REJECTED"]


@pytest.mark.parametrize(
    "state", ["OPEN", "PENDING", "NEW", "PARTIALLY_FILLED", "CANCELLED", "EXPIRED", "WORKING"]
)
def test_there_is_no_in_flight_lifecycle_state(state: str) -> None:
    """A paper order is terminal on construction; nothing advances it."""
    assert state not in PaperOrderStatus.__members__
    with pytest.raises(ValueError):
        PaperOrderStatus(state)


def test_members_are_constructible_from_their_own_value() -> None:
    assert PaperOrderStatus("FILLED") is PaperOrderStatus.FILLED
    assert PaperOrderStatus("REJECTED") is PaperOrderStatus.REJECTED


def test_members_compare_equal_to_their_string_value() -> None:
    assert PaperOrderStatus.FILLED == "FILLED"
    assert PaperOrderStatus.REJECTED == "REJECTED"


def test_members_are_strings() -> None:
    assert isinstance(PaperOrderStatus.FILLED, str)
    assert f"{PaperOrderStatus.REJECTED}" == "REJECTED"


def test_members_are_distinct_and_hashable() -> None:
    assert PaperOrderStatus.FILLED is not PaperOrderStatus.REJECTED
    assert len({PaperOrderStatus.FILLED, PaperOrderStatus.REJECTED}) == 2


def test_lowercase_is_not_silently_accepted() -> None:
    with pytest.raises(ValueError):
        PaperOrderStatus("filled")


def test_a_plain_string_is_not_a_status() -> None:
    assert not isinstance("FILLED", PaperOrderStatus)
