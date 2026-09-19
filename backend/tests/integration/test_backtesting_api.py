from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.backtesting.api import views as backtest_views
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


def _install_dependencies(monkeypatch: pytest.MonkeyPatch, asset: Asset) -> None:
    monkeypatch.setattr(
        backtest_views,
        "load_market_data_provider_configuration",
        lambda: SimpleNamespace(default_provider="mock"),
    )
    monkeypatch.setattr(
        backtest_views,
        "resolve_market_data_provider",
        lambda **_kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(backtest_views, "get_asset_resolver", lambda: SimpleNamespace())

    def executor(*_args: object, **_kwargs: object) -> MarketBarBatchResult:
        return MarketBarBatchResult(
            results=(
                MarketBarSymbolResult(
                    symbol=asset.symbol,
                    asset_id=asset.id,
                    status=MarketBarStatus.SUCCEEDED,
                    bars=(
                        _bar(asset.id, D1, 10.0),
                        _bar(asset.id, D2, 10.0),
                        _bar(asset.id, D3, 12.0),
                    ),
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

    monkeypatch.setattr(backtest_views, "execute_market_bar_query", executor)


def _payload(asset: Asset) -> dict[str, object]:
    return {
        "strategy": "BUY_AND_HOLD",
        "start": D1.isoformat(),
        "end": D4.isoformat(),
        "initial_cash": "100.00000000",
        "target_weights": [{"asset_id": str(asset.id), "weight": 1.0}],
        "commission_rate": 0.01,
        "slippage_rate": 0.0,
    }


@pytest.mark.django_db
def test_backtest_api_create_list_detail_and_owner_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    owner = User.objects.create_user(email="owner@example.com", password="password")
    other = User.objects.create_user(email="other@example.com", password="password")
    asset = Asset.objects.create(
        symbol="AAPL",
        name="Apple",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
        currency="USD",
    )
    _install_dependencies(monkeypatch, asset)

    client = APIClient()
    client.force_authenticate(user=owner)
    create_response = client.post(
        reverse("api-v1-backtest-run-list"),
        _payload(asset),
        format="json",
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    body = create_response.json()
    assert body["status"] == "SUCCEEDED"
    assert body["strategy"] == "BUY_AND_HOLD"
    assert body["provenance"]["engine_version"] == "0.2.0"
    assert body["provenance"]["backtest_method_version"] == "1.0"
    assert body["provenance"]["strategy_version"] == "1.0"
    assert body["result"]["provenance"]["aligned_period_start"] == D1.isoformat()
    assert body["result"]["decisions"][0]["decision_date"] == D1.isoformat()
    assert body["result"]["executions"][0]["execution_date"] == D2.isoformat()

    list_response = client.get(reverse("api-v1-backtest-run-list"))
    assert list_response.status_code == status.HTTP_200_OK
    assert len(list_response.json()) == 1

    run_id = body["id"]
    detail_response = client.get(reverse("api-v1-backtest-run-detail", args=[run_id]))
    assert detail_response.status_code == status.HTTP_200_OK

    client.force_authenticate(user=other)
    hidden_response = client.get(reverse("api-v1-backtest-run-detail", args=[run_id]))
    assert hidden_response.status_code == status.HTTP_404_NOT_FOUND
    assert client.get(reverse("api-v1-backtest-run-list")).json() == []


@pytest.mark.django_db
def test_backtest_api_rejects_target_weights_that_do_not_sum_to_one() -> None:
    user = User.objects.create_user(email="validation@example.com", password="password")
    asset = Asset.objects.create(
        symbol="MSFT",
        name="Microsoft",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
        currency="USD",
    )
    payload = _payload(asset)
    payload["target_weights"] = [{"asset_id": str(asset.id), "weight": 0.8}]

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(reverse("api-v1-backtest-run-list"), payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert "sum to one" in str(response.json()["errors"]["target_weights"]).lower()


@pytest.mark.django_db
def test_backtest_api_persists_expected_engine_failure_as_auditable_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.create_user(email="failed-api@example.com", password="password")
    asset = Asset.objects.create(
        symbol="VTI",
        name="Vanguard Total Stock Market ETF",
        asset_type=AssetType.ETF,
        exchange="NYSE",
        currency="USD",
    )
    monkeypatch.setattr(
        backtest_views,
        "load_market_data_provider_configuration",
        lambda: SimpleNamespace(default_provider="mock"),
    )
    monkeypatch.setattr(
        backtest_views,
        "resolve_market_data_provider",
        lambda **_kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(backtest_views, "get_asset_resolver", lambda: SimpleNamespace())

    def executor(*_args: object, **_kwargs: object) -> MarketBarBatchResult:
        return MarketBarBatchResult(
            results=(
                MarketBarSymbolResult(
                    symbol=asset.symbol,
                    asset_id=asset.id,
                    status=MarketBarStatus.SUCCEEDED,
                    bars=(_bar(asset.id, D1, 100.0),),
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

    monkeypatch.setattr(backtest_views, "execute_market_bar_query", executor)

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        reverse("api-v1-backtest-run-list"),
        _payload(asset),
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["status"] == "FAILED"
    assert body["result"] is None
    assert body["failure_code"] == "BACKTEST_INSUFFICIENT_HISTORY"
    assert "at least two complete-case" in body["failure_message"]
