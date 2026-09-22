"""Futures bounded context package.

A futures contract is identified by the exchange-defined product it belongs to
and the date it expires. Provider symbols, the economic underlying, contract
multipliers, tick sizes, last trading days and settlement instants are all
deliberately absent: each is either a provider naming concern or an attribute
of a product specification that does not yet exist.

Derivative identity is kept separate from market-listing identity, so nothing
here imports ListingReference. This package models no continuous contract, no
rollover, no margin and no profit and loss.
"""

from .value_objects import (
    FuturesContract,
    FuturesProductReference,
    FuturesProductSpecification,
    InvalidFuturesContractError,
    InvalidFuturesProductReferenceError,
    InvalidFuturesProductSpecificationError,
)

__all__ = [
    "FuturesContract",
    "FuturesProductReference",
    "FuturesProductSpecification",
    "InvalidFuturesContractError",
    "InvalidFuturesProductReferenceError",
    "InvalidFuturesProductSpecificationError",
]
