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
from apps.rebalancing.models import TargetAllocation, TargetAllocationWeight
from apps.rebalancing.services import (
    CreateHistoricalRebalanceComparisonCommand,
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
        executor=lambda *_args, **_kwargs: batch,
    )

    assert comparison.provider == "mock"
    assert comparison.price_field == "adjusted_close"
    assert comparison.retrieved_at == RETRIEVED_AT
    assert comparison.result["assumptions"]["execution_timing"] == (
        "decision_at_t_execute_at_next_aligned_observation"
    )
    policies = comparison.result["policies"]
    assert [policy["name"] for policy in policies] == ["annual", "quarterly", "threshold"]
    assert policies[0]["events"][0]["decision_date"] == d1.isoformat()
    assert policies[0]["events"][0]["execution_date"] == d2.isoformat()
    assert policies[0]["summary"]["trade_count"] == 2
    assert any(item["code"] == "ACTUAL_LEDGER_ACTIVITY_IGNORED" for item in comparison.warnings)
