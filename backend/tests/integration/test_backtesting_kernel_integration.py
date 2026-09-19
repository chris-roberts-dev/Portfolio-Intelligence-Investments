from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from portfolio_engine.backtesting import (
    BACKTEST_METHOD_VERSION,
    BacktestDataProvenance,
    BacktestInitialPosition,
    OrderIntent,
    OrderSide,
    StrategyContext,
    run_backtest,
)
from portfolio_engine.contracts.market_data import PriceBar
from portfolio_engine.version import PORTFOLIO_ENGINE_VERSION

A = UUID("00000000-0000-0000-0000-000000000001")
D1 = date(2026, 1, 2)
D2 = date(2026, 1, 5)
D3 = date(2026, 1, 6)
RETRIEVED_AT = datetime(2026, 1, 6, 22, 0, tzinfo=UTC)


@dataclass
class ReduceOnceStrategy:
    name: str = "integration-reduce-once"
    version: str = "1.0"
    minimum_history_observations: int = 1

    def generate_orders(self, context: StrategyContext) -> tuple[OrderIntent, ...]:
        if context.as_of == D1:
            return (OrderIntent(asset_id=A, side=OrderSide.SELL, quantity=2.0),)
        return ()


def _bar(trade_date: date, price: float) -> PriceBar:
    return PriceBar(
        asset_id=A,
        trade_date=trade_date,
        open=price,
        high=price,
        low=price,
        close=price,
        adjusted_close=price,
        volume=100,
        source="csv",
        retrieved_at=RETRIEVED_AT,
    )


def test_kernel_integrates_market_contract_execution_outputs_and_provenance() -> None:
    result = run_backtest(
        price_frames={A: (_bar(D1, 10.0), _bar(D2, 11.0), _bar(D3, 12.0))},
        initial_positions=(BacktestInitialPosition(asset_id=A, quantity=10.0),),
        initial_cash=0.0,
        strategy=ReduceOnceStrategy(),
        requested_period_start=D1,
        requested_period_end_exclusive=date(2026, 1, 7),
        data_provenance=BacktestDataProvenance(
            provider="csv",
            retrieved_at=RETRIEVED_AT,
            data_fingerprint="sha256:integration-fixture",
        ),
        commission_rate=0.01,
        slippage_rate=0.01,
    )

    assert result.aligned_dates == (D1, D2, D3)
    assert tuple(point.trade_date for point in result.equity_curve) == result.aligned_dates
    assert len(result.returns) == 2
    assert len(result.snapshots) == 3
    assert len(result.decisions) == 1
    assert len(result.executions) == 1
    assert result.trade_count == 1
    assert result.total_cost == pytest.approx(result.commission_cost + result.slippage_cost)
    assert result.assumptions.price_field == "adjusted_close"
    assert result.assumptions.execution_timing == (
        "decision_at_t_execute_at_next_aligned_observation"
    )
    assert result.assumptions.long_only is True
    assert result.assumptions.leverage is False
    assert result.provenance.provider == "csv"
    assert result.provenance.data_fingerprint == "sha256:integration-fixture"
    assert result.provenance.requested_period_start == D1
    assert result.provenance.requested_period_end_exclusive == date(2026, 1, 7)
    assert result.provenance.aligned_period_start == D1
    assert result.provenance.aligned_period_end == D3
    assert result.provenance.engine_version == PORTFOLIO_ENGINE_VERSION
    assert result.provenance.backtest_method_version == BACKTEST_METHOD_VERSION == "1.0"
    assert result.provenance.strategy_name == "integration-reduce-once"
    assert result.provenance.strategy_version == "1.0"
