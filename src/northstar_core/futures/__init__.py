"""Futures bounded context package.

A futures contract is identified by the exchange-defined product it belongs to
and the date it expires. Provider symbols, the economic underlying, contract
sizes, tick sizes, last trading days and settlement instants are all
deliberately absent from that identity. The only economic fact modelled is a
product's point value -- settlement currency per quote point per contract --
held in FuturesProductEconomics alongside, not inside, the contract.

Derivative identity is kept separate from market-listing identity, so nothing
here imports ListingReference. This package models no continuous contract, no
rollover, no margin and no profit and loss calculation.
"""

from .market_data import (
    FuturesOHLCVBar,
    FuturesReplaySnapshot,
    InvalidFuturesOHLCVBarError,
    InvalidFuturesReplaySnapshotError,
)
from .value_objects import (
    FuturesContract,
    FuturesPointValue,
    FuturesProductEconomics,
    FuturesProductReference,
    FuturesProductSpecification,
    InvalidFuturesContractError,
    InvalidFuturesPointValueError,
    InvalidFuturesProductEconomicsError,
    InvalidFuturesProductReferenceError,
    InvalidFuturesProductSpecificationError,
)

__all__ = [
    "FuturesContract",
    "FuturesOHLCVBar",
    "FuturesPointValue",
    "FuturesProductEconomics",
    "FuturesProductReference",
    "FuturesReplaySnapshot",
    "FuturesProductSpecification",
    "InvalidFuturesContractError",
    "InvalidFuturesOHLCVBarError",
    "InvalidFuturesPointValueError",
    "InvalidFuturesProductEconomicsError",
    "InvalidFuturesProductReferenceError",
    "InvalidFuturesReplaySnapshotError",
    "InvalidFuturesProductSpecificationError",
]
