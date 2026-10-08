"""Options bounded context package.

An option contract is identified by the exchange-defined product it belongs
to, the date it expires, its strike and the right it grants. The economic
underlying is held on the product specification, never on the contract.
Provider symbols and instrument keys, lot sizes, weekly or monthly
classification, exercise style and settlement method are all deliberately
absent from that identity.

An option premium is an observed quotation in premium points, zero or greater,
with no currency. The only economic fact modelled is a contract's point value
-- settlement currency per premium point per contract -- held in
OptionContractEconomics alongside, not inside, the contract. A contract's lot
size is folded into that one rate.

Options are a sibling of Futures, not a specialisation of it. Both build on the
shared derivatives package, and neither imports the other: an option product
that displays as ``NIFTY@NSE`` is a different type from the futures product of
the same name, and an option point value never values a futures contract.

Derivative identity is kept separate from market-listing identity, so nothing
here imports ListingReference. This package models no contract count, market
data, position, execution, profit and loss calculation, exercise, assignment,
settlement, volatility or sensitivity, and no strategy of several legs.
"""

from .value_objects import (
    InvalidOptionContractEconomicsError,
    InvalidOptionContractError,
    InvalidOptionPointValueError,
    InvalidOptionPremiumError,
    InvalidOptionProductReferenceError,
    InvalidOptionProductSpecificationError,
    InvalidOptionStrikeError,
    OptionContract,
    OptionContractEconomics,
    OptionPointValue,
    OptionPremium,
    OptionProductReference,
    OptionProductSpecification,
    OptionRight,
    OptionStrike,
)

__all__ = [
    "InvalidOptionContractEconomicsError",
    "InvalidOptionContractError",
    "InvalidOptionPointValueError",
    "InvalidOptionPremiumError",
    "InvalidOptionProductReferenceError",
    "InvalidOptionProductSpecificationError",
    "InvalidOptionStrikeError",
    "OptionContract",
    "OptionContractEconomics",
    "OptionPointValue",
    "OptionPremium",
    "OptionProductReference",
    "OptionProductSpecification",
    "OptionRight",
    "OptionStrike",
]
