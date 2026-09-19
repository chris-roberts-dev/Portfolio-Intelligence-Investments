from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.market_data.contracts import (
    MarketBarBatchMeta,
    MarketBarBatchResult,
    MarketBarInterval,
    MarketBarStatus,
    MarketBarSymbolResult,
)
from apps.portfolios.models import Portfolio, Transaction, TransactionType
from apps.portfolios.services.daily_performance import DailyPerformanceError
from apps.portfolios.services.trading_calendar import UsEquityTradingSessionCalendar
from apps.rebalancing.models import TargetAllocation, TargetAllocationWeight
from apps.rebalancing.services import (
    CreateHistoricalRebalanceComparisonCommand,
    RebalancingApplicationError,
    _build_actual_portfolio_baseline,
    _return_difference_pp_vs_actual,
    create_historical_rebalance_comparison,
)
from portfolio_engine.contracts.market_data import PriceBar

A = UUID("00000000-0000-0000-0000-000000000301")
B = UUID("00000000-0000-0000-0000-000000000302")
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


@pytest.mark.django_db
def test_historical_comparison_persists_required_rules_and_provenance() -> None:
    user = User.objects.create_user(email="owner@example.com", password="password")
    portfolio = Portfolio.objects.create(user=user, name="Owned")
    asset_a = Asset.objects.create(
        id=A,
        symbol="AAA",
        name="Asset A",
        asset_type=AssetType.STOCK,
        exchange="NYSE",
        currency="USD",
    )
    asset_b = Asset.objects.create(
        id=B,
        symbol="BBB",
        name="Asset B",
        asset_type=AssetType.ETF,
        exchange="NYSE",
        currency="USD",
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=datetime(2025, 12, 30, 12, 0, tzinfo=UTC),
        source_sequence=0,
        cash_amount=Decimal("100"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset=asset_a,
        occurred_at=datetime(2025, 12, 31, 12, 0, tzinfo=UTC),
        source_sequence=0,
        quantity=Decimal("10"),
        price=Decimal("10"),
        fees=Decimal("0"),
    )
    # Later real activity must not be silently incorporated into the hypothetical path.
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DIVIDEND,
        asset=asset_a,
        occurred_at=datetime(2026, 1, 6, 12, 0, tzinfo=UTC),
        source_sequence=0,
        cash_amount=Decimal("1"),
    )
    target = TargetAllocation.objects.create(user=user, portfolio=portfolio, name="Half")
    TargetAllocationWeight.objects.create(target=target, asset=asset_a, weight="0.5")
    TargetAllocationWeight.objects.create(target=target, asset=asset_b, weight="0.5")

    d1 = date(2026, 1, 2)
    d2 = date(2026, 1, 5)
    d3 = date(2026, 1, 6)
    batch = MarketBarBatchResult(
        results=(
            MarketBarSymbolResult(
                symbol="AAA",
                asset_id=A,
                status=MarketBarStatus.SUCCEEDED,
                bars=(_bar(A, d1, 10.0), _bar(A, d2, 20.0), _bar(A, d3, 20.0)),
            ),
            MarketBarSymbolResult(
                symbol="BBB",
                asset_id=B,
                status=MarketBarStatus.SUCCEEDED,
                bars=(_bar(B, d1, 10.0), _bar(B, d2, 10.0), _bar(B, d3, 10.0)),
            ),
        ),
        meta=MarketBarBatchMeta(
            provider="mock",
            retrieved_at=RETRIEVED_AT,
            interval=MarketBarInterval.DAILY,
            start=d1,
            end=date(2026, 1, 7),
        ),
    )

    comparison = create_historical_rebalance_comparison(
        user=user,
        command=CreateHistoricalRebalanceComparisonCommand(
            portfolio_id=portfolio.id,
            target_allocation_id=target.id,
            period_start=d1,
            period_end=d3,
            drift_threshold=0.1,
        ),
        provider_name="mock",
        resolver=SimpleNamespace(),  # type: ignore[arg-type]
        provider=SimpleNamespace(),  # type: ignore[arg-type]
        trading_calendar=UsEquityTradingSessionCalendar(),
        executor=lambda *_args, **_kwargs: batch,
    )

    assert comparison.provider == "mock"
    assert comparison.price_field == "adjusted_close"
    assert comparison.retrieved_at == RETRIEVED_AT
    assert comparison.engine_version == "0.2.0"
    assert comparison.result["provenance"]["engine_version"] == "0.2.0"
    assert comparison.result["provenance"]["method_version"] == "1.0"
    assert comparison.result["assumptions"]["execution_timing"] == (
        "decision_at_t_execute_at_next_aligned_observation"
    )
    policies = comparison.result["policies"]
    assert [policy["name"] for policy in policies] == ["annual", "quarterly", "threshold"]
    assert policies[0]["events"][0]["decision_date"] == d1.isoformat()
    assert policies[0]["events"][0]["execution_date"] == d2.isoformat()
    assert policies[0]["summary"]["trade_count"] == 2

    actual = comparison.result["actual_portfolio"]
    assert actual["available"] is True
    assert actual["return_method"] == "TIME_WEIGHTED"
    assert actual["starting_portfolio_value"] == pytest.approx(100.0)
    assert actual["ending_portfolio_value"] == pytest.approx(201.0)
    assert actual["cumulative_return"] == pytest.approx(1.01)
    assert actual["growth_of_100_start"] == pytest.approx(100.0)
    assert actual["growth_of_100_end"] == pytest.approx(201.0)
    assert [point["trade_date"] for point in actual["series"]] == [
        d1.isoformat(),
        d2.isoformat(),
        d3.isoformat(),
    ]
    assert policies[0]["summary"]["return_difference_pp_vs_actual"] == pytest.approx(-1.0)
    assert any(item["code"] == "ACTUAL_LEDGER_ACTIVITY_IGNORED" for item in comparison.warnings)


def test_percentage_point_difference_reference_case() -> None:
    assert _return_difference_pp_vs_actual(0.6952, 0.6040) == pytest.approx(9.12)


@pytest.mark.django_db
def test_actual_portfolio_inception_baseline_reports_sixty_point_four_percent() -> None:
    user = User.objects.create_user(email="inception@example.com", password="password")
    portfolio = Portfolio.objects.create(user=user, name="Inception")
    asset = Asset.objects.create(
        symbol="GROW",
        name="Growth Asset",
        asset_type=AssetType.STOCK,
        exchange="NYSE",
        currency="USD",
    )
    inception = date(2019, 12, 31)
    middle = date(2020, 1, 2)
    end = date(2020, 1, 3)
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=datetime(2019, 12, 31, 9, 0, tzinfo=UTC),
        source_sequence=0,
        cash_amount=Decimal("1000000"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset=asset,
        occurred_at=datetime(2019, 12, 31, 10, 0, tzinfo=UTC),
        source_sequence=0,
        quantity=Decimal("10000"),
        price=Decimal("100"),
        fees=Decimal("0"),
    )

    prices = (
        _bar(asset.id, inception, 100.0),
        _bar(asset.id, middle, 80.0),
        _bar(asset.id, end, 160.4),
    )

    def executor(query: object, **_kwargs: object) -> MarketBarBatchResult:
        return MarketBarBatchResult(
            results=(
                MarketBarSymbolResult(
                    symbol="GROW",
                    asset_id=asset.id,
                    status=MarketBarStatus.SUCCEEDED,
                    bars=prices,
                ),
            ),
            meta=MarketBarBatchMeta(
                provider="mock",
                retrieved_at=RETRIEVED_AT,
                interval=MarketBarInterval.DAILY,
                start=inception,
                end=date(2020, 1, 4),
            ),
        )

    baseline, warnings = _build_actual_portfolio_baseline(
        user=user,
        portfolio=portfolio,
        period_start=inception,
        period_end=end,
        aligned_dates=(inception, middle, end),
        provider_name="mock",
        resolver=SimpleNamespace(),  # type: ignore[arg-type]
        provider=SimpleNamespace(),  # type: ignore[arg-type]
        trading_calendar=UsEquityTradingSessionCalendar(),
        executor=executor,  # type: ignore[arg-type]
    )

    assert warnings == []
    assert baseline["starting_portfolio_value"] == pytest.approx(1_000_000.0)
    assert baseline["ending_portfolio_value"] == pytest.approx(1_604_000.0)
    assert baseline["cumulative_return"] == pytest.approx(0.604)
    assert baseline["growth_of_100_end"] == pytest.approx(160.4)
    assert baseline["cumulative_return"] != pytest.approx(0.8362)


@pytest.mark.django_db
def test_actual_portfolio_baseline_changes_when_comparison_start_changes() -> None:
    user = User.objects.create_user(email="period@example.com", password="password")
    portfolio = Portfolio.objects.create(user=user, name="Period sensitive")
    asset = Asset.objects.create(
        symbol="PERD",
        name="Period Asset",
        asset_type=AssetType.STOCK,
        exchange="NYSE",
        currency="USD",
    )
    inception = date(2019, 12, 31)
    later_start = date(2020, 1, 2)
    end = date(2020, 1, 3)
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=datetime(2019, 12, 31, 9, 0, tzinfo=UTC),
        source_sequence=0,
        cash_amount=Decimal("1000000"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset=asset,
        occurred_at=datetime(2019, 12, 31, 10, 0, tzinfo=UTC),
        source_sequence=0,
        quantity=Decimal("10000"),
        price=Decimal("100"),
        fees=Decimal("0"),
    )

    prices = (
        _bar(asset.id, inception, 100.0),
        _bar(asset.id, later_start, 80.0),
        _bar(asset.id, end, 160.4),
    )

    def executor(query: object, **_kwargs: object) -> MarketBarBatchResult:
        return MarketBarBatchResult(
            results=(
                MarketBarSymbolResult(
                    symbol="PERD",
                    asset_id=asset.id,
                    status=MarketBarStatus.SUCCEEDED,
                    bars=prices,
                ),
            ),
            meta=MarketBarBatchMeta(
                provider="mock",
                retrieved_at=RETRIEVED_AT,
                interval=MarketBarInterval.DAILY,
                start=inception,
                end=date(2020, 1, 4),
            ),
        )

    inception_baseline, _ = _build_actual_portfolio_baseline(
        user=user,
        portfolio=portfolio,
        period_start=inception,
        period_end=end,
        aligned_dates=(inception, later_start, end),
        provider_name="mock",
        resolver=SimpleNamespace(),  # type: ignore[arg-type]
        provider=SimpleNamespace(),  # type: ignore[arg-type]
        trading_calendar=UsEquityTradingSessionCalendar(),
        executor=executor,  # type: ignore[arg-type]
    )
    later_baseline, _ = _build_actual_portfolio_baseline(
        user=user,
        portfolio=portfolio,
        period_start=later_start,
        period_end=end,
        aligned_dates=(later_start, end),
        provider_name="mock",
        resolver=SimpleNamespace(),  # type: ignore[arg-type]
        provider=SimpleNamespace(),  # type: ignore[arg-type]
        trading_calendar=UsEquityTradingSessionCalendar(),
        executor=executor,  # type: ignore[arg-type]
    )

    assert inception_baseline["cumulative_return"] == pytest.approx(0.604)
    assert later_baseline["starting_portfolio_value"] == pytest.approx(800_000.0)
    assert later_baseline["cumulative_return"] == pytest.approx(1.005)
    assert later_baseline["cumulative_return"] != inception_baseline["cumulative_return"]


@pytest.mark.django_db
def test_historical_comparison_rejects_unfunded_initial_state_before_market_data() -> None:
    user = User.objects.create_user(email="unfunded@example.com", password="password")
    portfolio = Portfolio.objects.create(user=user, name="Unfunded")
    asset = Asset.objects.create(
        symbol="VOID",
        name="Unfunded Asset",
        asset_type=AssetType.STOCK,
        exchange="NYSE",
        currency="USD",
    )
    target = TargetAllocation.objects.create(user=user, portfolio=portfolio, name="Full target")
    TargetAllocationWeight.objects.create(target=target, asset=asset, weight="1")
    executor_called = False

    def executor(*_args: object, **_kwargs: object) -> MarketBarBatchResult:
        nonlocal executor_called
        executor_called = True
        raise AssertionError("market data must not be requested for an invalid initial state")

    with pytest.raises(RebalancingApplicationError) as exc_info:
        create_historical_rebalance_comparison(
            user=user,
            command=CreateHistoricalRebalanceComparisonCommand(
                portfolio_id=portfolio.id,
                target_allocation_id=target.id,
                period_start=date(2026, 1, 2),
                period_end=date(2026, 1, 6),
                drift_threshold=0.05,
            ),
            provider_name="mock",
            resolver=SimpleNamespace(),  # type: ignore[arg-type]
            provider=SimpleNamespace(),  # type: ignore[arg-type]
            trading_calendar=UsEquityTradingSessionCalendar(),
            executor=executor,  # type: ignore[arg-type]
        )

    assert exc_info.value.code == "INVALID_INITIAL_PORTFOLIO_STATE"
    assert "positive investable value" in str(exc_info.value)
    assert executor_called is False


@pytest.mark.django_db
def test_historical_comparison_rejects_negative_cash_before_market_data() -> None:
    user = User.objects.create_user(email="negative-cash@example.com", password="password")
    portfolio = Portfolio.objects.create(user=user, name="Negative cash")
    asset = Asset.objects.create(
        symbol="NEGC",
        name="Negative Cash Asset",
        asset_type=AssetType.STOCK,
        exchange="NYSE",
        currency="USD",
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.WITHDRAWAL,
        occurred_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
        source_sequence=0,
        cash_amount=Decimal("100"),
    )
    target = TargetAllocation.objects.create(user=user, portfolio=portfolio, name="Full target")
    TargetAllocationWeight.objects.create(target=target, asset=asset, weight="1")
    executor_called = False

    def executor(*_args: object, **_kwargs: object) -> MarketBarBatchResult:
        nonlocal executor_called
        executor_called = True
        raise AssertionError("market data must not be requested for negative starting cash")

    with pytest.raises(RebalancingApplicationError) as exc_info:
        create_historical_rebalance_comparison(
            user=user,
            command=CreateHistoricalRebalanceComparisonCommand(
                portfolio_id=portfolio.id,
                target_allocation_id=target.id,
                period_start=date(2026, 1, 2),
                period_end=date(2026, 1, 6),
                drift_threshold=0.05,
            ),
            provider_name="mock",
            resolver=SimpleNamespace(),  # type: ignore[arg-type]
            provider=SimpleNamespace(),  # type: ignore[arg-type]
            trading_calendar=UsEquityTradingSessionCalendar(),
            executor=executor,  # type: ignore[arg-type]
        )

    assert exc_info.value.code == "INVALID_INITIAL_PORTFOLIO_STATE"
    assert "negative cash balance" in str(exc_info.value)
    assert executor_called is False


@pytest.mark.django_db
def test_actual_portfolio_baseline_warns_when_exact_twr_is_unavailable(monkeypatch) -> None:
    user = User.objects.create_user(email="baseline@example.com", password="password")
    portfolio = Portfolio.objects.create(user=user, name="Baseline")

    def fail_daily_performance(**_kwargs: object) -> object:
        raise DailyPerformanceError("required adjusted-close history is unavailable")

    monkeypatch.setattr(
        "apps.rebalancing.services.calculate_owned_portfolio_daily_performance",
        fail_daily_performance,
    )

    d1 = date(2026, 1, 2)
    d2 = date(2026, 1, 5)
    baseline, warnings = _build_actual_portfolio_baseline(
        user=user,
        portfolio=portfolio,
        period_start=d1,
        period_end=d2,
        aligned_dates=(d1, d2),
        provider_name="mock",
        resolver=SimpleNamespace(),  # type: ignore[arg-type]
        provider=SimpleNamespace(),  # type: ignore[arg-type]
        trading_calendar=UsEquityTradingSessionCalendar(),
        executor=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError()),
    )

    assert baseline["available"] is False
    assert baseline["cumulative_return"] is None
    assert baseline["series"] == []
    assert warnings == [
        {
            "code": "ACTUAL_PORTFOLIO_COMPARISON_UNAVAILABLE",
            "message": (
                "Actual portfolio performance is unavailable for the exact aligned "
                "comparison period: required adjusted-close history is unavailable"
            ),
        }
    ]
