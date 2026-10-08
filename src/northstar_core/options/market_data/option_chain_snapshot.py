"""Immutable point-in-time cross-section of one option expiration.

An OptionChainSnapshot holds, for one product and one expiration at one instant,
every exact option contract the snapshot's builder treats as listed, each with
the canonical daily bar stamped exactly at that instant when one exists. It
keeps three things apart:

- listed: a contract is an entry;
- observed: an entry carries a daily bar;
- selected: nothing here chooses, ranks, filters or scores a contract.

An entry without a bar says only that no canonical daily bar is held for that
contract at the snapshot instant. It does not say that the contract did not
trade, that a provider returned no candle, that anyone tried to acquire one, or
that the contract is illiquid.

Which contracts count as listed at an instant, and which instant a trading date
names, are decided outside Core; the snapshot only guarantees its own shape.
It carries no trading date, timezone, underlying value, open interest, days to
expiry, moneyness, volatility, sensitivity, bid or ask, provider metadata,
listing timestamp, score or selection status.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.derivatives import ExpirationDate
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime, Timeframe
from northstar_core.options.market_data.option_ohlcv_bar import OptionOHLCVBar
from northstar_core.options.value_objects import (
    OptionContract,
    OptionProductReference,
    OptionRight,
)

_DAILY = Timeframe("1d")

# Canonical entry order: strike ascending, then CALL before PUT. Stated here
# rather than borrowed from OptionContract, which defines no ordering.
_RIGHT_RANK = {OptionRight.CALL: 0, OptionRight.PUT: 1}


class InvalidOptionChainEntryError(ValidationError):
    """Raised when an option chain entry is invalid."""


class InvalidOptionChainSnapshotError(ValidationError):
    """Raised when an option chain snapshot is invalid."""


def _sort_key(contract: OptionContract) -> tuple:
    return (contract.strike.value, _RIGHT_RANK[contract.right])


@dataclass(frozen=True, slots=True)
class OptionChainEntry:
    """One exact option contract of a chain, with its daily bar when one is held.

    ``daily_bar`` is None exactly when no canonical daily bar is held for this
    contract at the snapshot instant; nothing more is implied by its absence.
    """

    contract: OptionContract
    daily_bar: OptionOHLCVBar | None

    def __post_init__(self) -> None:
        if not isinstance(self.contract, OptionContract):
            raise InvalidOptionChainEntryError(
                "OptionChainEntry contract must be an OptionContract value."
            )
        if self.daily_bar is not None:
            if not isinstance(self.daily_bar, OptionOHLCVBar):
                raise InvalidOptionChainEntryError(
                    "OptionChainEntry daily bar must be an OptionOHLCVBar or None."
                )
            if self.daily_bar.contract != self.contract:
                raise InvalidOptionChainEntryError(
                    f"OptionChainEntry daily bar is for {self.daily_bar.contract}, "
                    f"not {self.contract}."
                )

    def __str__(self) -> str:
        if self.daily_bar is None:
            return f"{self.contract}: no daily bar"
        return f"{self.contract}: C={self.daily_bar.close} V={self.daily_bar.volume}"


@dataclass(frozen=True, slots=True)
class OptionChainSnapshot:
    """Every listed contract of one option expiration at one instant.

    Invariants:
        - At least one entry, as an exact tuple of OptionChainEntry.
        - Every entry's contract has the snapshot's product and expiration.
        - Contracts are unique, ordered by strike ascending, then CALL before PUT.
        - Every daily bar present is stamped exactly at ``as_of`` with the
          daily ``1d`` timeframe; no earlier or later bar stands in for it.
    """

    product: OptionProductReference
    expiration_date: ExpirationDate
    as_of: PointInTime
    entries: tuple[OptionChainEntry, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.product, OptionProductReference):
            raise InvalidOptionChainSnapshotError(
                "OptionChainSnapshot product must be an OptionProductReference value."
            )
        if not isinstance(self.expiration_date, ExpirationDate):
            raise InvalidOptionChainSnapshotError(
                "OptionChainSnapshot expiration date must be an ExpirationDate value."
            )
        if not isinstance(self.as_of, PointInTime):
            raise InvalidOptionChainSnapshotError(
                "OptionChainSnapshot as-of must be a PointInTime value."
            )
        if not isinstance(self.entries, tuple) or not all(
            isinstance(entry, OptionChainEntry) for entry in self.entries
        ):
            raise InvalidOptionChainSnapshotError(
                "OptionChainSnapshot entries must be a tuple of OptionChainEntry values."
            )
        if not self.entries:
            raise InvalidOptionChainSnapshotError(
                "OptionChainSnapshot must hold at least one entry."
            )

        seen: set[OptionContract] = set()
        for entry in self.entries:
            contract = entry.contract
            if contract.product != self.product:
                raise InvalidOptionChainSnapshotError(
                    f"OptionChainSnapshot entry {contract} is not a {self.product} contract."
                )
            if contract.expiration_date != self.expiration_date:
                raise InvalidOptionChainSnapshotError(
                    f"OptionChainSnapshot entry {contract} does not expire on "
                    f"{self.expiration_date}."
                )
            if contract in seen:
                raise InvalidOptionChainSnapshotError(
                    f"OptionChainSnapshot holds {contract} more than once."
                )
            seen.add(contract)
            bar = entry.daily_bar
            if bar is not None:
                if bar.point_in_time != self.as_of:
                    raise InvalidOptionChainSnapshotError(
                        f"OptionChainSnapshot daily bar for {contract} is stamped "
                        f"{bar.point_in_time}, not {self.as_of}."
                    )
                if bar.timeframe != _DAILY:
                    raise InvalidOptionChainSnapshotError(
                        f"OptionChainSnapshot bar for {contract} has timeframe "
                        f"{bar.timeframe}, not {_DAILY}."
                    )

        keys = [_sort_key(entry.contract) for entry in self.entries]
        if keys != sorted(keys):
            raise InvalidOptionChainSnapshotError(
                "OptionChainSnapshot entries must be ordered by strike ascending, "
                "then CALL before PUT."
            )

    def __str__(self) -> str:
        return (
            f"{self.product} {self.expiration_date} as of {self.as_of}: "
            f"{len(self.entries)} contracts"
        )
