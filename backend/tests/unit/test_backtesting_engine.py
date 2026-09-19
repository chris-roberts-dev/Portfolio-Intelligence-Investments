from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from portfolio_engine.backtesting import (
    BacktestDataProvenance,
    BacktestError,
    BacktestErrorCode,
    BacktestInitialPosition,
    OrderIntent,
    OrderSide,
    StrategyContext,
    run_backtest,
)
from portfolio_engine.contracts.market_data import PriceBar

A = UUID("00000000-0000-0000-0000-000000000001")
B = UUID("00000000-0000-0000-0000-000000000002")
D1 = date(2026, 1, 2)
D2 = date(2026, 1, 5)
D3 = date(2026, 1, 6)
D4 = date(2026, 1, 7)
RETRIEVED_AT = datetime(2026, 1, 7, 22, 0, tzinfo=UTC)
PROVENANCE = BacktestDataProvenance(
    provider="mock",
    retrieved_at=RETRIEVED_AT,
    data_fingerprint="unit-fixture",
)


def _bar(asset_id: UUID, trade_date: date, price: float | None) -> PriceBar:
    return PriceBar(
        asset_id=asset_id,
        trade_date=trade_date,
        open=price,
        high=price,
        low=price,
        close=price,
        adjusted_close=price,
        volume=100,
        source="mock",
        retrieved_at=RETRIEVED_AT,
    )


def _frame(asset_id: UUID, prices: tuple[tuple[date, float | None], ...]) -> tuple[PriceBar, ...]:
    return tuple(_bar(asset_id, trade_date, price) for trade_date, price in prices)


@dataclass
class OneShotStrategy:
    orders: tuple[OrderIntent, ...]
    decision_date: date = D1
    name: str = "unit-one-shot"
    version: str = "1.0"
    minimum_history_observations: int = 1

    def generate_orders(self, context: StrategyContext) -> tuple[OrderIntent, ...]:
        return self.orders if context.as_of == self.decision_date else ()


@dataclass
class RecordingStrategy:
    name: str = "recording"
    version: str = "1.0"
    minimum_history_observations: int = 1
    seen: list[tuple[date, tuple[date, ...]]] = field(default_factory=list)

    def generate_orders(self, context: StrategyContext) -> tuple[OrderIntent, ...]:
        visible_dates = tuple(bar.trade_date for frame in context.history.values() for bar in frame)
        self.seen.append((context.as_of, visible_dates))
        return ()


def test_manual_sell_fixture_proves_state_cost_turnover_and_return() -> None:
    strategy = OneShotStrategy(orders=(OrderIntent(asset_id=A, side=OrderSide.SELL, quantity=5.0),))
    result = run_backtest(
        price_frames={A: _frame(A, ((D1, 10.0), (D2, 10.0)))},
        initial_positions=(BacktestInitialPosition(asset_id=A, quantity=10.0),),
        initial_cash=0.0,
        strategy=strategy,
        requested_period_start=D1,
        requested_period_end_exclusive=D3,
        data_provenance=PROVENANCE,
        commission_rate=0.01,
        slippage_rate=0.0,
    )

    assert result.initial_value == pytest.approx(100.0)
    assert result.ending_value == pytest.approx(99.5)
    assert result.cumulative_return == pytest.approx(-0.005)
    assert result.turnover == pytest.approx(0.5)
    assert result.commission_cost == pytest.approx(0.5)
    assert result.slippage_cost == pytest.approx(0.0)
    assert result.total_cost == pytest.approx(0.5)
    assert result.trade_count == 1

    decision = result.decisions[0]
    event = result.executions[0]
    fill = event.fills[0]
    assert decision.decision_date == D1
    assert event.execution_date == D2
    assert event.execution_date > event.decision_date
    assert fill.quantity == pytest.approx(5.0)
    assert fill.reference_price == pytest.approx(10.0)
    assert fill.fill_price == pytest.approx(10.0)
    assert fill.fill_notional == pytest.approx(50.0)
    assert fill.commission_cost == pytest.approx(0.5)
    assert result.snapshots[-1].cash == pytest.approx(49.5)
    assert result.snapshots[-1].positions[0].quantity == pytest.approx(5.0)
    assert result.snapshots[-1].total_value == pytest.approx(99.5)
    assert result.returns[0].simple_return == pytest.approx(-0.005)


def test_costed_buy_is_proportionally_scaled_to_preserve_nonnegative_cash() -> None:
    strategy = OneShotStrategy(orders=(OrderIntent(asset_id=A, side=OrderSide.BUY, quantity=10.0),))
    result = run_backtest(
        price_frames={A: _frame(A, ((D1, 10.0), (D2, 10.0)))},
        initial_positions=(),
        initial_cash=100.0,
        strategy=strategy,
        requested_period_start=D1,
        requested_period_end_exclusive=D3,
        data_provenance=PROVENANCE,
        commission_rate=0.01,
        slippage_rate=0.01,
    )

    event = result.executions[0]
    fill = event.fills[0]
    assert event.buy_scale < 1.0
    assert fill.quantity < 10.0
    assert fill.fill_price == pytest.approx(10.1)
    assert result.snapshots[-1].cash == pytest.approx(0.0, abs=1e-10)
    assert result.snapshots[-1].positions[0].quantity > 0.0
    assert event.commission_cost > 0.0
    assert event.slippage_cost > 0.0
    assert event.post_trade_value < event.pre_trade_value
    assert result.warnings
    assert result.warnings[-1].code.value == "BUY_SCALED_TO_AVAILABLE_CASH"


def test_strategy_context_never_exposes_future_prices() -> None:
    strategy = RecordingStrategy()
    result = run_backtest(
        price_frames={
            A: _frame(A, ((D1, 10.0), (D2, 11.0), (D3, 12.0))),
            B: _frame(B, ((D1, 20.0), (D2, 19.0), (D3, 18.0))),
        },
        initial_positions=(),
        initial_cash=100.0,
        strategy=strategy,
        requested_period_start=D1,
        requested_period_end_exclusive=D4,
        data_provenance=PROVENANCE,
    )

    assert len(strategy.seen) == len(result.aligned_dates)
    for as_of, visible_dates in strategy.seen:
        assert visible_dates
        assert max(visible_dates) <= as_of


def test_future_price_changes_cannot_change_decision_at_t() -> None:
    @dataclass
    class CurrentCloseStrategy:
        name: str = "current-close"
        version: str = "1.0"
        minimum_history_observations: int = 1

        def generate_orders(self, context: StrategyContext) -> tuple[OrderIntent, ...]:
            if context.as_of != D1:
                return ()
            current_price = context.history[A][-1].adjusted_close
            assert current_price is not None
            if current_price >= 10.0:
                return (OrderIntent(asset_id=A, side=OrderSide.BUY, quantity=1.0),)
            return ()

    kwargs = {
        "initial_positions": (),
        "initial_cash": 100.0,
        "strategy": CurrentCloseStrategy(),
        "requested_period_start": D1,
        "requested_period_end_exclusive": D3,
        "data_provenance": PROVENANCE,
    }
    first = run_backtest(
        price_frames={A: _frame(A, ((D1, 10.0), (D2, 10.0)))},
        **kwargs,
    )
    changed_future = run_backtest(
        price_frames={A: _frame(A, ((D1, 10.0), (D2, 100.0)))},
        **kwargs,
    )

    assert first.decisions[0] == changed_future.decisions[0]
    assert first.decisions[0].decision_date == D1
    assert first.executions[0].execution_date == changed_future.executions[0].execution_date == D2


def test_warmup_blocks_strategy_until_sufficient_backward_history_exists() -> None:
    @dataclass
    class WarmupStrategy:
        name: str = "warmup"
        version: str = "1.0"
        minimum_history_observations: int = 3
        called: list[date] = field(default_factory=list)

        def generate_orders(self, context: StrategyContext) -> tuple[OrderIntent, ...]:
            self.called.append(context.as_of)
            return ()

    strategy = WarmupStrategy()
    run_backtest(
        price_frames={A: _frame(A, ((D1, 10.0), (D2, 10.0), (D3, 10.0), (D4, 10.0)))},
        initial_positions=(),
        initial_cash=100.0,
        strategy=strategy,
        requested_period_start=D1,
        requested_period_end_exclusive=date(2026, 1, 8),
        data_provenance=PROVENANCE,
    )

    assert strategy.called == [D3, D4]


def test_sell_that_would_create_short_position_fails_explicitly() -> None:
    strategy = OneShotStrategy(
        orders=(OrderIntent(asset_id=A, side=OrderSide.SELL, quantity=11.0),)
    )
    with pytest.raises(BacktestError) as exc_info:
        run_backtest(
            price_frames={A: _frame(A, ((D1, 10.0), (D2, 10.0)))},
            initial_positions=(BacktestInitialPosition(asset_id=A, quantity=10.0),),
            initial_cash=0.0,
            strategy=strategy,
            requested_period_start=D1,
            requested_period_end_exclusive=D3,
            data_provenance=PROVENANCE,
        )

    assert exc_info.value.code is BacktestErrorCode.INSUFFICIENT_POSITION


def test_final_date_order_is_recorded_but_not_executed_at_same_close() -> None:
    strategy = OneShotStrategy(
        orders=(OrderIntent(asset_id=A, side=OrderSide.BUY, quantity=1.0),),
        decision_date=D2,
    )
    result = run_backtest(
        price_frames={A: _frame(A, ((D1, 10.0), (D2, 11.0)))},
        initial_positions=(),
        initial_cash=100.0,
        strategy=strategy,
        requested_period_start=D1,
        requested_period_end_exclusive=D3,
        data_provenance=PROVENANCE,
    )

    assert result.decisions[-1].decision_date == D2
    assert result.executions == ()
    assert result.warnings[-1].code.value == "UNEXECUTED_FINAL_ORDERS"


def test_execution_uses_adjusted_close_not_raw_close() -> None:
    strategy = OneShotStrategy(orders=(OrderIntent(asset_id=A, side=OrderSide.BUY, quantity=1.0),))
    frame = (
        PriceBar(
            asset_id=A,
            trade_date=D1,
            open=100.0,
            high=100.0,
            low=100.0,
            close=100.0,
            adjusted_close=10.0,
            volume=100,
            source="mock",
            retrieved_at=RETRIEVED_AT,
        ),
        PriceBar(
            asset_id=A,
            trade_date=D2,
            open=200.0,
            high=200.0,
            low=200.0,
            close=200.0,
            adjusted_close=20.0,
            volume=100,
            source="mock",
            retrieved_at=RETRIEVED_AT,
        ),
    )
    result = run_backtest(
        price_frames={A: frame},
        initial_positions=(),
        initial_cash=100.0,
        strategy=strategy,
        requested_period_start=D1,
        requested_period_end_exclusive=D3,
        data_provenance=PROVENANCE,
    )

    assert result.executions[0].fills[0].reference_price == pytest.approx(20.0)
    assert result.assumptions.price_field == "adjusted_close"


def test_preperiod_history_can_satisfy_warmup_without_expanding_evaluation_period() -> None:
    pre1 = date(2025, 12, 30)
    pre2 = date(2025, 12, 31)

    @dataclass
    class WarmupStrategy:
        name: str = "preperiod-warmup"
        version: str = "1.0"
        minimum_history_observations: int = 3
        called: list[date] = field(default_factory=list)

        def generate_orders(self, context: StrategyContext) -> tuple[OrderIntent, ...]:
            self.called.append(context.as_of)
            return ()

    strategy = WarmupStrategy()
    result = run_backtest(
        price_frames={
            A: _frame(
                A,
                (
                    (pre1, 8.0),
                    (pre2, 9.0),
                    (D1, 10.0),
                    (D2, 11.0),
                ),
            )
        },
        initial_positions=(),
        initial_cash=100.0,
        strategy=strategy,
        requested_period_start=D1,
        requested_period_end_exclusive=D3,
        data_provenance=PROVENANCE,
    )

    assert result.aligned_dates == (D1, D2)
    assert strategy.called == [D1, D2]
    assert result.provenance.requested_period_start == D1
    assert result.provenance.aligned_period_start == D1
