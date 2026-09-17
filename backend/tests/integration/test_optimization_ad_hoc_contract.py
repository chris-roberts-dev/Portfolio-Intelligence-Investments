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
from apps.optimization.api.serializers import OptimizationRunCreateRequestSerializer
from apps.optimization.models import (
    OptimizationRun,
    OptimizationRunMethod,
    OptimizationRunSource,
    OptimizationRunStatus,
)
from apps.optimization.services import (
    BaselineWeight,
    CreateOptimizationRunCommand,
    OptimizationApplicationError,
    create_optimization_run,
)
from apps.portfolios.models import Portfolio

AAPL_ID = UUID("00000000-0000-0000-0000-000000000011")
MSFT_ID = UUID("00000000-0000-0000-0000-000000000012")


def _asset(asset_id: UUID, symbol: str) -> Asset:
    return Asset.objects.create(
        id=asset_id,
        symbol=symbol,
        name=f"{symbol} Inc.",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
        currency="USD",
        is_active=True,
    )


@pytest.mark.django_db
def test_ad_hoc_request_requires_explicit_assets_and_no_portfolio() -> None:
    serializer = OptimizationRunCreateRequestSerializer(
        data={
            "source_type": "AD_HOC",
            "portfolio_id": None,
            "method": "MINIMUM_VARIANCE",
            "start": "2025-01-01",
            "end": "2026-01-01",
            "asset_ids": [str(AAPL_ID), str(MSFT_ID)],
            "risk_free_rate_annual": 0.035,
        }
    )
    assert serializer.is_valid(), serializer.errors
    command = serializer.to_command()
    assert command.source_type is OptimizationRunSource.AD_HOC
    assert command.portfolio_id is None
    assert command.requested_asset_ids == (AAPL_ID, MSFT_ID)
    assert command.risk_free_rate_annual == pytest.approx(0.035)


@pytest.mark.django_db
def test_ad_hoc_service_does_not_require_assets_to_be_portfolio_holdings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.create_user(email="adhoc@example.com", password="password")
    _asset(AAPL_ID, "AAPL")
    _asset(MSFT_ID, "MSFT")

    monkeypatch.setattr(
        "apps.optimization.services._load_price_frames",
        lambda **_: ({str(AAPL_ID): (), str(MSFT_ID): ()}, datetime(2026, 1, 1, tzinfo=UTC)),
    )
    monkeypatch.setattr(
        "apps.optimization.services.estimate_historical_inputs",
        lambda *_: SimpleNamespace(
            asset_keys=(str(AAPL_ID), str(MSFT_ID)),
            expected_returns=(0.1, 0.08),
            covariance=((0.04, 0.01), (0.01, 0.03)),
            observations=100,
            covariance_rank=2,
        ),
    )
    monkeypatch.setattr(
        "apps.optimization.services.build_problem",
        lambda **_: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "apps.optimization.services._execute_method",
        lambda **_: {
            "portfolio": {
                "method": "MINIMUM_VARIANCE",
                "weights": [
                    {"asset_id": str(AAPL_ID), "weight": 0.4},
                    {"asset_id": str(MSFT_ID), "weight": 0.6},
                ],
                "expected_return": 0.09,
                "expected_volatility": 0.15,
                "sharpe_ratio": 0.4,
                "target_return": None,
            },
            "frontier": [],
        },
    )
    monkeypatch.setattr(
        "apps.optimization.services._data_fingerprint",
        lambda **_: "abc123",
    )

    run = create_optimization_run(
        user=user,
        command=CreateOptimizationRunCommand(
            portfolio_id=None,
            source_type=OptimizationRunSource.AD_HOC,
            method=OptimizationRunMethod.MINIMUM_VARIANCE,
            period_start=date(2025, 1, 1),
            period_end=date(2026, 1, 1),
            requested_asset_ids=(AAPL_ID, MSFT_ID),
            risk_free_rate_annual=0.035,
        ),
        provider_name="mock",
        resolver=SimpleNamespace(),  # type: ignore[arg-type]
        provider=SimpleNamespace(),  # type: ignore[arg-type]
        executor=SimpleNamespace(),  # type: ignore[arg-type]
    )

    assert run.status == OptimizationRunStatus.SUCCEEDED
    assert run.source_type == OptimizationRunSource.AD_HOC
    assert run.portfolio_id is None
    assert run.included_asset_ids == [str(AAPL_ID), str(MSFT_ID)]
    assert float(run.risk_free_rate_annual) == pytest.approx(0.035)


@pytest.mark.django_db
def test_complete_baseline_is_validated_before_persistence() -> None:
    user = User.objects.create_user(email="baseline@example.com", password="password")
    _asset(AAPL_ID, "AAPL")
    _asset(MSFT_ID, "MSFT")

    with pytest.raises(
        OptimizationApplicationError,
        match="sum to one",
    ):
        create_optimization_run(
            user=user,
            command=CreateOptimizationRunCommand(
                portfolio_id=None,
                source_type=OptimizationRunSource.AD_HOC,
                method=OptimizationRunMethod.EQUAL_WEIGHT,
                period_start=date(2025, 1, 1),
                period_end=date(2026, 1, 1),
                requested_asset_ids=(AAPL_ID, MSFT_ID),
                baseline_weights=(
                    BaselineWeight(AAPL_ID, 0.4),
                    BaselineWeight(MSFT_ID, 0.4),
                ),
            ),
            provider_name="mock",
            resolver=SimpleNamespace(),  # type: ignore[arg-type]
            provider=SimpleNamespace(),  # type: ignore[arg-type]
            executor=SimpleNamespace(),  # type: ignore[arg-type]
        )


@pytest.mark.django_db
def test_portfolio_source_remains_owner_scoped() -> None:
    owner = User.objects.create_user(email="owner@example.com", password="password")
    other = User.objects.create_user(email="other@example.com", password="password")
    portfolio = Portfolio.objects.create(user=owner, name="Owned")

    with pytest.raises(Portfolio.DoesNotExist):
        create_optimization_run(
            user=other,
            command=CreateOptimizationRunCommand(
                portfolio_id=portfolio.id,
                source_type=OptimizationRunSource.PORTFOLIO,
                method=OptimizationRunMethod.EQUAL_WEIGHT,
                period_start=date(2025, 1, 1),
                period_end=date(2026, 1, 1),
            ),
            provider_name="mock",
            resolver=SimpleNamespace(),  # type: ignore[arg-type]
            provider=SimpleNamespace(),  # type: ignore[arg-type]
            executor=SimpleNamespace(),  # type: ignore[arg-type]
        )


@pytest.mark.django_db
def test_owned_run_list_and_detail_include_ad_hoc_source_without_cross_user_disclosure() -> None:
    owner = User.objects.create_user(email="owner-list@example.com", password="password")
    other = User.objects.create_user(email="other-list@example.com", password="password")

    run = OptimizationRun.objects.create(
        user=owner,
        source_type=OptimizationRunSource.AD_HOC,
        portfolio=None,
        benchmark_asset=None,
        status=OptimizationRunStatus.PENDING,
        method=OptimizationRunMethod.EQUAL_WEIGHT,
        period_start=date(2025, 1, 1),
        period_end=date(2026, 1, 1),
        provider="mock",
        included_asset_ids=[str(AAPL_ID)],
        baseline_weights=[],
        parameters={
            "source_type": "AD_HOC",
            "requested_asset_ids": [str(AAPL_ID)],
            "bounds": [],
            "baseline_weights": [],
            "risk_free_rate_annual": 0.0,
            "frontier_points": 25,
        },
    )

    owner_client = APIClient()
    owner_client.force_authenticate(user=owner)
    response = owner_client.get(reverse("api-v1-optimization-run-list"))
    assert response.status_code == status.HTTP_200_OK
    assert response.data[0]["source_type"] == "AD_HOC"
    assert response.data[0]["portfolio_id"] is None

    other_client = APIClient()
    other_client.force_authenticate(user=other)
    response = other_client.get(
        reverse("api-v1-optimization-run-detail", kwargs={"run_id": run.id})
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_ad_hoc_request_rejects_missing_explicit_asset_universe() -> None:
    serializer = OptimizationRunCreateRequestSerializer(
        data={
            "source_type": "AD_HOC",
            "method": "MINIMUM_VARIANCE",
            "start": "2025-01-01",
            "end": "2026-01-01",
        }
    )
    assert not serializer.is_valid()
    assert "asset_ids" in serializer.errors


@pytest.mark.django_db
def test_ad_hoc_run_persists_failed_state_for_inactive_asset() -> None:
    user = User.objects.create_user(email="inactive@example.com", password="password")
    Asset.objects.create(
        id=AAPL_ID,
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
        currency="USD",
        is_active=False,
    )

    run = create_optimization_run(
        user=user,
        command=CreateOptimizationRunCommand(
            portfolio_id=None,
            source_type=OptimizationRunSource.AD_HOC,
            method=OptimizationRunMethod.EQUAL_WEIGHT,
            period_start=date(2025, 1, 1),
            period_end=date(2026, 1, 1),
            requested_asset_ids=(AAPL_ID,),
        ),
        provider_name="mock",
        resolver=SimpleNamespace(),  # type: ignore[arg-type]
        provider=SimpleNamespace(),  # type: ignore[arg-type]
        executor=SimpleNamespace(),  # type: ignore[arg-type]
    )

    assert run.status == OptimizationRunStatus.FAILED
    assert run.failure_code == "ASSET_UNSUPPORTED"
