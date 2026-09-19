from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.backtesting.models import BacktestRunStatus, BacktestStrategyName
from apps.backtesting.services import (
    BacktestTargetWeightInput,
    CreateBacktestRunCommand,
    create_backtest_run,
)
from apps.market_data.contracts import (
    MarketBarBatchMeta,
    MarketBarBatchResult,
    MarketBarInterval,
    MarketBarStatus,
    MarketBarSymbolResult,
)
from portfolio_engine.contracts.market_data import PriceBar

D1 = date(2026, 1, 2)
D2 = date(2026, 1, 5)
D3 = date(2026, 1, 6)
D4 = date(2026, 1, 7)
RETRIEVED_AT = datetime(2026, 1, 6, 22, 0, tzinfo=UTC)


def _bar(asset_id: UUID, trade_date: date, price: float) -> PriceBar:
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


def _batch(asset: Asset, prices: tuple[tuple[date, float], ...]) -> MarketBarBatchResult:
    return MarketBarBatchResult(
        results=(
            MarketBarSymbolResult(
                symbol=asset.symbol,
                asset_id=asset.id,
                status=MarketBarStatus.SUCCEEDED,
                bars=tuple(_bar(asset.id, trade_date, price) for trade_date, price in prices),
            ),
        ),
        meta=MarketBarBatchMeta(
            provider="mock",
            retrieved_at=RETRIEVED_AT,
            interval=MarketBarInterval.DAILY,
            start=D1,
            end=D4,
        ),
    )


def _command(asset_id: UUID) -> CreateBacktestRunCommand:
    return CreateBacktestRunCommand(
        strategy=BacktestStrategyName.BUY_AND_HOLD,
        period_start=D1,
        period_end_exclusive=D4,
        initial_cash=100.0,
        target_weights=(BacktestTargetWeightInput(asset_id=asset_id, weight=1.0),),
        commission_rate=0.01,
        slippage_rate=0.0,
    )


@pytest.mark.django_db
def test_buy_and_hold_run_persists_reproducible_result_and_provenance() -> None:
    user = User.objects.create_user(email="backtest@example.com", password="password")
    asset = Asset.objects.create(
        symbol="AAPL",
        name="Apple",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
        currency="USD",
    )

    def executor(*_args: object, **_kwargs: object) -> MarketBarBatchResult:
        return _batch(asset, ((D1, 10.0), (D2, 10.0), (D3, 12.0)))

    run = create_backtest_run(
        user=user,
        command=_command(asset.id),
        provider_name="mock",
        resolver=SimpleNamespace(),  # type: ignore[arg-type]
        provider=SimpleNamespace(),  # type: ignore[arg-type]
        executor=executor,  # type: ignore[arg-type]
    )

    assert run.status == BacktestRunStatus.SUCCEEDED
    assert run.user == user
    assert run.strategy == BacktestStrategyName.BUY_AND_HOLD
    assert run.included_asset_ids == [str(asset.id)]
    assert run.engine_version == "0.2.0"
    assert run.method_version == "1.0"
    assert run.strategy_version == "1.0"
    assert run.data_retrieved_at == RETRIEVED_AT
    assert len(run.data_fingerprint) == 64
    assert run.failure_code == ""
    assert run.failure_message == ""
    assert run.result is not None
    assert run.result["provenance"]["strategy_name"] == "BUY_AND_HOLD"
    assert run.result["provenance"]["strategy_version"] == "1.0"
    assert run.result["provenance"]["backtest_method_version"] == "1.0"
    assert run.result["provenance"]["requested_period_start"] == D1.isoformat()
    assert run.result["provenance"]["aligned_period_start"] == D1.isoformat()
    assert run.result["decisions"][0]["decision_date"] == D1.isoformat()
    assert run.result["executions"][0]["execution_date"] == D2.isoformat()
    assert run.result["summary"]["trade_count"] == 1
    assert run.result["summary"]["total_cost"] > 0.0
    assert run.parameters["rebalance_after_initial_execution"] is False


@pytest.mark.django_db
def test_buy_and_hold_identical_inputs_persist_equivalent_result_payloads() -> None:
    user = User.objects.create_user(email="repeat@example.com", password="password")
    asset = Asset.objects.create(
        symbol="MSFT",
        name="Microsoft",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
        currency="USD",
    )

    def executor(*_args: object, **_kwargs: object) -> MarketBarBatchResult:
        return _batch(asset, ((D1, 20.0), (D2, 21.0), (D3, 22.0)))

    kwargs = {
        "user": user,
        "command": _command(asset.id),
        "provider_name": "mock",
        "resolver": SimpleNamespace(),
        "provider": SimpleNamespace(),
        "executor": executor,
    }
    first = create_backtest_run(**kwargs)  # type: ignore[arg-type]
    second = create_backtest_run(**kwargs)  # type: ignore[arg-type]

    assert first.status == second.status == BacktestRunStatus.SUCCEEDED
    assert first.data_fingerprint == second.data_fingerprint
    assert first.result == second.result


@pytest.mark.django_db
def test_insufficient_history_persists_failed_run_instead_of_success() -> None:
    user = User.objects.create_user(email="failed@example.com", password="password")
    asset = Asset.objects.create(
        symbol="VTI",
        name="Vanguard Total Stock Market ETF",
        asset_type=AssetType.ETF,
        exchange="NYSE",
        currency="USD",
    )

    def executor(*_args: object, **_kwargs: object) -> MarketBarBatchResult:
        return _batch(asset, ((D1, 100.0),))

    run = create_backtest_run(
        user=user,
        command=_command(asset.id),
        provider_name="mock",
        resolver=SimpleNamespace(),  # type: ignore[arg-type]
        provider=SimpleNamespace(),  # type: ignore[arg-type]
        executor=executor,  # type: ignore[arg-type]
    )

    assert run.status == BacktestRunStatus.FAILED
    assert run.result is None
    assert run.failure_code == "BACKTEST_INSUFFICIENT_HISTORY"
    assert "at least two complete-case" in run.failure_message
    assert run.data_retrieved_at == RETRIEVED_AT
    assert len(run.data_fingerprint) == 64
