"""Options bounded context package.

An option contract is identified by the exchange-defined product it belongs
to, the date it expires, its strike and the right it grants. The economic
underlying is held on the product specification, never on the contract.
Provider symbols and instrument keys, lot sizes, weekly or monthly
classification, exercise style and settlement method are all deliberately
absent from that identity.

Options are a sibling of Futures, not a specialisation of it. Both build on the
shared derivatives package, and neither imports the other: an option product
that displays as ``NIFTY@NSE`` is a different type from the futures product of
the same name.

Derivative identity is kept separate from market-listing identity, so nothing
here imports ListingReference. This package models no premium, economics,
contract count, market data, position, execution, exercise, assignment,
settlement, volatility or sensitivity, and no strategy of several legs.
"""

from .value_objects import (
    InvalidOptionContractError,
    InvalidOptionProductReferenceError,
    InvalidOptionProductSpecificationError,
    InvalidOptionStrikeError,
    OptionContract,
    OptionProductReference,
    OptionProductSpecification,
    OptionRight,
    OptionStrike,
)

__all__ = [
    "InvalidOptionContractError",
    "InvalidOptionProductReferenceError",
    "InvalidOptionProductSpecificationError",
    "InvalidOptionStrikeError",
    "OptionContract",
    "OptionProductReference",
    "OptionProductSpecification",
    "OptionRight",
    "OptionStrike",
]
