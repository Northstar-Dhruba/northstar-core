"""The futures paper value chain holds zero and negative quotations end to end."""

from __future__ import annotations

from decimal import Decimal

import pytest

from northstar_core.derivatives import ExpirationDate, QuoteValue
from northstar_core.foundation.value_objects import ExchangeCode, PointInTime, Symbol
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.paper_trading import (
    FuturesContractCount,
    FuturesExecutionIntent,
    FuturesPaperFill,
    FuturesPaperOrder,
    FuturesPaperPortfolio,
    FuturesPosition,
    OrderSide,
    PaperFillIdentity,
    PaperOrderIdentity,
    PaperPortfolioIdentity,
)
from northstar_core.strategy import StrategyIdentity

_CONTRACT = FuturesContract(
    FuturesProductReference(Symbol("CL"), ExchangeCode("NYMEX")), ExpirationDate("2020-05-19")
)


@pytest.mark.parametrize(
    ("quote", "side", "net"), [("-37.63", OrderSide.BUY, 1), ("0", OrderSide.SELL, -1)]
)
def test_the_whole_chain_holds_the_quotation(quote: str, side: OrderSide, net: int) -> None:
    portfolio_identity = PaperPortfolioIdentity("paper-1")
    strategy_identity = StrategyIdentity("alpha")
    intent = FuturesExecutionIntent(
        portfolio_identity=portfolio_identity,
        contract=_CONTRACT,
        side=side,
        contracts=FuturesContractCount(1),
        strategy_identity=strategy_identity,
        decided_at=PointInTime("2020-04-17T22:00:00Z"),
    )
    order = FuturesPaperOrder(PaperOrderIdentity("order-1"), intent)
    fill = FuturesPaperFill(
        identity=PaperFillIdentity("fill-1"),
        order_identity=order.identity,
        intent=order.intent,
        contracts=intent.contracts,
        fill_quote=QuoteValue(Decimal(quote)),
        filled_at=PointInTime("2020-04-20T22:00:00Z"),
    )
    position = FuturesPosition(fill.contract, net, fill.fill_quote)
    portfolio = FuturesPaperPortfolio(
        identity=portfolio_identity,
        strategy_identity=strategy_identity,
        positions=(position,),
        as_of=fill.filled_at,
    )

    assert fill.fill_quote.value == Decimal(quote)
    assert position.average_entry.value == Decimal(quote)
    assert portfolio.get_position(_CONTRACT) == position
