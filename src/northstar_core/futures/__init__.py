"""Futures bounded context package.

A futures contract is identified by the exchange-defined product it belongs to
and the date it expires. Provider symbols, the economic underlying, contract
sizes, tick sizes, last trading days and settlement instants are all
deliberately absent from that identity. The only economic fact modelled is a
contract's point value -- settlement currency per quote point per contract --
held in FuturesContractEconomics alongside, not inside, the contract. The
product-level FuturesProductEconomics is retained for historical reference only
and is not the profit and loss authority.

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
    FuturesContractEconomics,
    FuturesPointValue,
    FuturesProductEconomics,
    FuturesProductReference,
    FuturesProductSpecification,
    InvalidFuturesContractEconomicsError,
    InvalidFuturesContractError,
    InvalidFuturesPointValueError,
    InvalidFuturesProductEconomicsError,
    InvalidFuturesProductReferenceError,
    InvalidFuturesProductSpecificationError,
)

__all__ = [
    "FuturesContract",
    "FuturesContractEconomics",
    "FuturesOHLCVBar",
    "FuturesPointValue",
    "FuturesProductEconomics",
    "FuturesProductReference",
    "FuturesReplaySnapshot",
    "FuturesProductSpecification",
    "InvalidFuturesContractEconomicsError",
    "InvalidFuturesContractError",
    "InvalidFuturesOHLCVBarError",
    "InvalidFuturesPointValueError",
    "InvalidFuturesProductEconomicsError",
    "InvalidFuturesProductReferenceError",
    "InvalidFuturesReplaySnapshotError",
    "InvalidFuturesProductSpecificationError",
]
