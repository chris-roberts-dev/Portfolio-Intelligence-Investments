"""Integration tests for authenticated portfolio lifecycle mutations."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.optimization.models import OptimizationRun, OptimizationRunMethod
from apps.portfolios.models import Portfolio, Transaction, TransactionType


def authenticated_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_authenticated_user_creates_server_owned_usd_portfolio() -> None:
    owner = User.objects.create_user(
        email="portfolio-create-owner@example.com",
        password="test-password-123",
    )
    other = User.objects.create_user(
        email="portfolio-create-other@example.com",
        password="test-password-123",
    )

    response = authenticated_client(owner).post(
        reverse("api-v1-portfolio-list"),
        {
            "name": "  Retirement Portfolio  ",
            "user_id": str(other.id),
            "base_currency": "EUR",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    created = Portfolio.objects.get(id=response.data["id"])
    assert created.user == owner
    assert created.name == "Retirement Portfolio"
    assert created.base_currency == "USD"
    assert response.data["base_currency"] == "USD"
    assert response.data["ledger_inception_at"] is None


@pytest.mark.django_db
def test_portfolio_list_and_detail_expose_earliest_ledger_inception() -> None:
    owner = User.objects.create_user(
        email="portfolio-inception-owner@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        user=owner,
        name="Historical portfolio",
    )
    later = datetime(2021, 5, 3, 14, 0, tzinfo=UTC)
    earliest = datetime(2020, 1, 2, 14, 0, tzinfo=UTC)
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=later,
        source_sequence=2,
        cash_amount=Decimal("500.00"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=earliest,
        source_sequence=1,
        cash_amount=Decimal("1000.00"),
    )
    client = authenticated_client(owner)

    list_response = client.get(reverse("api-v1-portfolio-list"))
    detail_response = client.get(
        reverse(
            "api-v1-portfolio-detail",
            kwargs={"portfolio_id": portfolio.id},
        )
    )

    assert list_response.status_code == status.HTTP_200_OK
    assert detail_response.status_code == status.HTTP_200_OK

    list_payload = list_response.json()
    detail_payload = detail_response.json()

    list_inception = datetime.fromisoformat(
        list_payload[0]["ledger_inception_at"].replace("Z", "+00:00")
    )
    detail_inception = datetime.fromisoformat(
        detail_payload["ledger_inception_at"].replace("Z", "+00:00")
    )

    assert list_inception == earliest
    assert detail_inception == earliest


@pytest.mark.django_db
def test_portfolio_create_returns_structured_name_validation_error() -> None:
    owner = User.objects.create_user(
        email="portfolio-create-invalid@example.com",
        password="test-password-123",
    )

    response = authenticated_client(owner).post(
        reverse("api-v1-portfolio-list"),
        {"name": "   "},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "VALIDATION_ERROR"
    assert "name" in response.data["errors"]
    assert Portfolio.objects.count() == 0


@pytest.mark.django_db
def test_owner_can_rename_portfolio() -> None:
    owner = User.objects.create_user(
        email="portfolio-rename-owner@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        user=owner,
        name="Before",
    )

    response = authenticated_client(owner).patch(
        reverse(
            "api-v1-portfolio-detail",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"name": "After"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    portfolio.refresh_from_db()
    assert portfolio.name == "After"
    assert response.data["name"] == "After"


@pytest.mark.django_db
def test_user_cannot_rename_another_users_portfolio() -> None:
    owner = User.objects.create_user(
        email="portfolio-hidden-owner@example.com",
        password="test-password-123",
    )
    attacker = User.objects.create_user(
        email="portfolio-hidden-attacker@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        user=owner,
        name="Private",
    )

    response = authenticated_client(attacker).patch(
        reverse(
            "api-v1-portfolio-detail",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"name": "Hijacked"},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    portfolio.refresh_from_db()
    assert portfolio.name == "Private"


@pytest.mark.django_db
def test_portfolio_mutations_require_authentication() -> None:
    response = APIClient().post(
        reverse("api-v1-portfolio-list"),
        {"name": "Anonymous"},
        format="json",
    )

    assert response.status_code in {
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    }
    assert Portfolio.objects.count() == 0


@pytest.mark.django_db
def test_owner_can_delete_empty_portfolio() -> None:
    owner = User.objects.create_user(
        email="portfolio-delete-owner@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(user=owner, name="Empty portfolio")

    response = authenticated_client(owner).delete(
        reverse(
            "api-v1-portfolio-detail",
            kwargs={"portfolio_id": portfolio.id},
        )
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    assert not Portfolio.objects.filter(id=portfolio.id).exists()


@pytest.mark.django_db
def test_portfolio_delete_is_hidden_across_user_boundary() -> None:
    owner = User.objects.create_user(
        email="portfolio-delete-private-owner@example.com",
        password="test-password-123",
    )
    attacker = User.objects.create_user(
        email="portfolio-delete-private-attacker@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(user=owner, name="Private portfolio")

    response = authenticated_client(attacker).delete(
        reverse(
            "api-v1-portfolio-detail",
            kwargs={"portfolio_id": portfolio.id},
        )
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert Portfolio.objects.filter(id=portfolio.id).exists()


@pytest.mark.django_db
def test_portfolio_delete_requires_authentication() -> None:
    owner = User.objects.create_user(
        email="portfolio-delete-auth-owner@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(user=owner, name="Private portfolio")

    response = APIClient().delete(
        reverse(
            "api-v1-portfolio-detail",
            kwargs={"portfolio_id": portfolio.id},
        )
    )

    assert response.status_code in {
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    }
    assert Portfolio.objects.filter(id=portfolio.id).exists()


@pytest.mark.django_db
def test_portfolio_delete_is_blocked_by_transaction_history() -> None:
    owner = User.objects.create_user(
        email="portfolio-delete-ledger@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(user=owner, name="Ledger portfolio")
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=datetime(2026, 9, 1, 14, 0, tzinfo=UTC),
        cash_amount=Decimal("1000.00"),
    )

    response = authenticated_client(owner).delete(
        reverse(
            "api-v1-portfolio-detail",
            kwargs={"portfolio_id": portfolio.id},
        )
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data == {
        "code": "PORTFOLIO_DELETE_BLOCKED",
        "detail": (
            "This portfolio contains retained transaction or analytical history "
            "and cannot currently be permanently deleted."
        ),
    }
    assert Portfolio.objects.filter(id=portfolio.id).exists()
    assert Transaction.objects.filter(portfolio=portfolio).exists()


@pytest.mark.django_db
def test_portfolio_delete_is_blocked_by_persisted_analytical_history() -> None:
    owner = User.objects.create_user(
        email="portfolio-delete-analysis@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(user=owner, name="Analyzed portfolio")
    OptimizationRun.objects.create(
        user=owner,
        portfolio=portfolio,
        method=OptimizationRunMethod.EQUAL_WEIGHT,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 2, 1),
        provider="mock",
        included_asset_ids=[],
    )

    response = authenticated_client(owner).delete(
        reverse(
            "api-v1-portfolio-detail",
            kwargs={"portfolio_id": portfolio.id},
        )
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data["code"] == "PORTFOLIO_DELETE_BLOCKED"
    assert Portfolio.objects.filter(id=portfolio.id).exists()
    assert OptimizationRun.objects.filter(portfolio=portfolio).exists()


@pytest.mark.django_db
def test_owner_can_select_and_clear_canonical_benchmark() -> None:
    owner = User.objects.create_user(
        email="benchmark-owner@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        user=owner,
        name="Benchmark portfolio",
    )
    benchmark = Asset.objects.create(
        symbol="SPY",
        name="SPDR S&P 500 ETF Trust",
        asset_type=AssetType.ETF,
        exchange="NYSEARCA",
        currency="USD",
        is_active=True,
    )

    select_response = authenticated_client(owner).patch(
        reverse(
            "api-v1-portfolio-benchmark",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"benchmark_asset_id": str(benchmark.id)},
        format="json",
    )

    assert select_response.status_code == status.HTTP_200_OK
    portfolio.refresh_from_db()
    assert portfolio.benchmark_asset_id == benchmark.id
    assert select_response.data["benchmark_asset_id"] == str(benchmark.id)

    clear_response = authenticated_client(owner).patch(
        reverse(
            "api-v1-portfolio-benchmark",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"benchmark_asset_id": None},
        format="json",
    )

    assert clear_response.status_code == status.HTTP_200_OK
    portfolio.refresh_from_db()
    assert portfolio.benchmark_asset_id is None
    assert clear_response.data["benchmark_asset_id"] is None


@pytest.mark.django_db
def test_benchmark_selection_rejects_inactive_or_unknown_asset_identity() -> None:
    owner = User.objects.create_user(
        email="benchmark-invalid@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(user=owner, name="Benchmark portfolio")
    inactive = Asset.objects.create(
        symbol="OLD",
        name="Inactive ETF",
        asset_type=AssetType.ETF,
        exchange="NYSEARCA",
        currency="USD",
        is_active=False,
    )

    for benchmark_asset_id in (inactive.id, uuid4()):
        response = authenticated_client(owner).patch(
            reverse(
                "api-v1-portfolio-benchmark",
                kwargs={"portfolio_id": portfolio.id},
            ),
            {"benchmark_asset_id": str(benchmark_asset_id)},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "VALIDATION_ERROR"
        assert response.data["errors"]["benchmark_asset_id"] == [
            "Benchmark asset must reference an active canonical USD stock or ETF."
        ]

    portfolio.refresh_from_db()
    assert portfolio.benchmark_asset_id is None


@pytest.mark.django_db
def test_benchmark_selection_requires_authentication() -> None:
    owner = User.objects.create_user(
        email="benchmark-auth-owner@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(user=owner, name="Private")

    response = APIClient().patch(
        reverse(
            "api-v1-portfolio-benchmark",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"benchmark_asset_id": None},
        format="json",
    )

    assert response.status_code in {
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    }


@pytest.mark.django_db
def test_user_cannot_change_another_users_benchmark() -> None:
    owner = User.objects.create_user(
        email="benchmark-private-owner@example.com",
        password="test-password-123",
    )
    attacker = User.objects.create_user(
        email="benchmark-private-attacker@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(user=owner, name="Private")
    benchmark = Asset.objects.create(
        symbol="SPY",
        name="SPDR S&P 500 ETF Trust",
        asset_type=AssetType.ETF,
        exchange="NYSEARCA",
        currency="USD",
        is_active=True,
    )

    response = authenticated_client(attacker).patch(
        reverse(
            "api-v1-portfolio-benchmark",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"benchmark_asset_id": str(benchmark.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    portfolio.refresh_from_db()
    assert portfolio.benchmark_asset_id is None
