from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.portfolios.models import Portfolio
from apps.rebalancing.models import TargetAllocation, TargetAllocationWeight
from apps.rebalancing.services import (
    CreateRebalanceSimulationCommand,
    create_rebalance_simulation,
)


@pytest.mark.django_db
def test_current_rebalance_simulation_persists_server_authoritative_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.create_user(email="owner@example.com", password="password")
    portfolio = Portfolio.objects.create(user=user, name="Owned")
    asset = Asset.objects.create(
        id=UUID("00000000-0000-0000-0000-000000000201"),
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
        currency="USD",
    )
    target = TargetAllocation.objects.create(user=user, portfolio=portfolio, name="Half cash")
    TargetAllocationWeight.objects.create(target=target, asset=asset, is_cash=False, weight="0.5")
    TargetAllocationWeight.objects.create(target=target, asset=None, is_cash=True, weight="0.5")
    as_of = datetime(2026, 9, 17, 13, 0, tzinfo=UTC)

    fake_current = SimpleNamespace(
        is_complete=True,
        valuation=SimpleNamespace(
            positions=(SimpleNamespace(asset_id=asset.id, market_value=800.0),),
            cash_value=200.0,
            total_market_value=1000.0,
        ),
        allocation=SimpleNamespace(),
        provenance=SimpleNamespace(
            provider="mock",
            price_field="close",
            retrieved_at=as_of,
        ),
        warnings=(),
    )
    monkeypatch.setattr(
        "apps.rebalancing.services.value_owned_portfolio",
        lambda **_: fake_current,
    )
    simulation = create_rebalance_simulation(
        user=user,
        command=CreateRebalanceSimulationCommand(
            portfolio_id=portfolio.id,
            target_allocation_id=target.id,
            drift_threshold=0.1,
        ),
        as_of=as_of,
        provider_name="mock",
        resolver=SimpleNamespace(),  # type: ignore[arg-type]
        provider=SimpleNamespace(),  # type: ignore[arg-type]
        trading_calendar=SimpleNamespace(),  # type: ignore[arg-type]
    )
    lines = simulation.result["lines"]
    asset_line = next(line for line in lines if line["asset_id"] == str(asset.id))
    assert asset_line["current_weight"] == pytest.approx(0.8)
    assert asset_line["target_weight"] == pytest.approx(0.5)
    assert asset_line["trade_notional"] == pytest.approx(-300.0)
    assert simulation.result["rules"]["threshold_triggered"] is True
