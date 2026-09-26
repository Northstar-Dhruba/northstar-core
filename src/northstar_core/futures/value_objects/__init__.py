"""Futures Value Objects."""

from .futures_contract import FuturesContract, InvalidFuturesContractError
from .futures_point_value import FuturesPointValue, InvalidFuturesPointValueError
from .futures_product_economics import (
    FuturesProductEconomics,
    InvalidFuturesProductEconomicsError,
)
from .futures_product_reference import (
    FuturesProductReference,
    InvalidFuturesProductReferenceError,
)
from .futures_product_specification import (
    FuturesProductSpecification,
    InvalidFuturesProductSpecificationError,
)

__all__ = [
    "FuturesContract",
    "FuturesPointValue",
    "FuturesProductEconomics",
    "FuturesProductReference",
    "FuturesProductSpecification",
    "InvalidFuturesContractError",
    "InvalidFuturesPointValueError",
    "InvalidFuturesProductEconomicsError",
    "InvalidFuturesProductReferenceError",
    "InvalidFuturesProductSpecificationError",
]
