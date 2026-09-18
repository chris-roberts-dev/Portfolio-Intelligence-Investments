"""Integration tests for bounded atomic CSV transaction import."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.market_data.services.asset_discovery import (
    CanonicalAssetResolutionBatch,
    CanonicalAssetResolutionOutcome,
    CanonicalAssetResolutionStatus,
)
from apps.portfolios.models import Portfolio, Transaction, TransactionType
from apps.portfolios.services.ledger import replay_portfolio_ledger
from apps.portfolios.services.transaction_ingestion import (
    MAX_TRANSACTION_IMPORT_BYTES,
    MAX_TRANSACTION_IMPORT_ROWS,
)


def authenticated_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def owner() -> User:
    return User.objects.create_user(
        email="csv-owner@example.com",
        password="test-password-123",
    )


@pytest.fixture
def portfolio(owner: User) -> Portfolio:
    return Portfolio.objects.create(
        user=owner,
        name="CSV Portfolio",
    )


@pytest.fixture
def asset() -> Asset:
    return Asset.objects.create(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
    )


def csv_text(asset_id: str) -> str:
    return (
        "transaction_type,occurred_at,asset_id,quantity,price,fees,cash_amount\n"
        " deposit ,2026-09-15T13:00:00Z,,,,0,1000.00\n"
        f"BUY,2026-09-15T14:00:00Z,{asset_id},2,100,1,\n"
    )


@pytest.mark.django_db
def test_preview_normalizes_rows_without_persisting(
    owner: User,
    portfolio: Portfolio,
    asset: Asset,
) -> None:
    response = authenticated_client(owner).post(
        reverse(
            "api-v1-portfolio-transaction-import-preview",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"csv_text": csv_text(str(asset.id))},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["row_count"] == 2
    assert response.data["valid_count"] == 2
    assert response.data["invalid_count"] == 0
    assert response.data["can_import"] is True
    assert response.data["atomic"] is True
    assert response.data["rows"][0]["transaction_type"] == "DEPOSIT"
    assert response.data["rows"][1]["asset_symbol"] == "AAPL"
    assert response.data["rows"][1]["transaction_type"] == "BUY"
    assert Transaction.objects.count() == 0


@pytest.mark.django_db
def test_preview_reports_unknown_asset_identity_without_substitution(
    owner: User,
    portfolio: Portfolio,
) -> None:
    unknown_id = "00000000-0000-0000-0000-000000000099"
    content = (
        "transaction_type,occurred_at,asset_id,quantity,price,fees,cash_amount\n"
        f"BUY,2026-09-15T14:00:00Z,{unknown_id},1,100,0,\n"
    )

    response = authenticated_client(owner).post(
        reverse(
            "api-v1-portfolio-transaction-import-preview",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"csv_text": content},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["can_import"] is False
    assert response.data["rows"][0]["valid"] is False
    assert response.data["rows"][0]["issues"][0]["code"] == "ASSET_NOT_FOUND"
    assert Transaction.objects.count() == 0


@pytest.mark.django_db
def test_preview_reports_malformed_row_fields_with_stable_codes(
    owner: User,
    portfolio: Portfolio,
    asset: Asset,
) -> None:
    content = (
        "transaction_type,occurred_at,asset_id,quantity,price,fees,cash_amount\n"
        f"BUY,2026-09-15T14:00:00,{asset.id},not-a-number,100,0,\n"
    )

    response = authenticated_client(owner).post(
        reverse(
            "api-v1-portfolio-transaction-import-preview",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"csv_text": content},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["can_import"] is False
    codes = {issue["code"] for issue in response.data["rows"][0]["issues"]}
    assert codes == {"TIMEZONE_REQUIRED", "INVALID_DECIMAL"}
    assert Transaction.objects.count() == 0


@pytest.mark.django_db
def test_confirm_is_atomic_when_any_row_is_invalid(
    owner: User,
    portfolio: Portfolio,
    asset: Asset,
) -> None:
    content = (
        "transaction_type,occurred_at,asset_id,quantity,price,fees,cash_amount\n"
        "DEPOSIT,2026-09-15T13:00:00Z,,,,0,1000.00\n"
        f"SELL,2026-09-15T14:00:00Z,{asset.id},1,100,0,\n"
    )

    response = authenticated_client(owner).post(
        reverse(
            "api-v1-portfolio-transaction-import-confirm",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"csv_text": content},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "IMPORT_VALIDATION_FAILED"
    assert response.data["preview"]["invalid_count"] == 1
    assert response.data["preview"]["rows"][1]["issues"][0]["code"] == ("NEGATIVE_POSITION")
    assert Transaction.objects.count() == 0


@pytest.mark.django_db
def test_confirm_commits_complete_valid_import_and_replays_ledger(
    owner: User,
    portfolio: Portfolio,
    asset: Asset,
) -> None:
    response = authenticated_client(owner).post(
        reverse(
            "api-v1-portfolio-transaction-import-confirm",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"csv_text": csv_text(str(asset.id))},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["imported_count"] == 2
    assert Transaction.objects.count() == 2

    replay = replay_portfolio_ledger(portfolio)
    assert replay.cash_balance == Decimal("799")
    assert replay.positions[0].asset_id == asset.id
    assert replay.positions[0].quantity == Decimal("2")


@pytest.mark.django_db
def test_import_respects_chronological_ledger_order_even_when_csv_rows_are_out_of_order(
    owner: User,
    portfolio: Portfolio,
    asset: Asset,
) -> None:
    content = (
        "transaction_type,occurred_at,asset_id,quantity,price,fees,cash_amount\n"
        f"SELL,2026-09-15T15:00:00Z,{asset.id},1,110,0,\n"
        f"BUY,2026-09-15T14:00:00Z,{asset.id},1,100,0,\n"
    )

    response = authenticated_client(owner).post(
        reverse(
            "api-v1-portfolio-transaction-import-preview",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"csv_text": content},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["can_import"] is True
    assert Transaction.objects.count() == 0


@pytest.mark.django_db
def test_import_rejects_invalid_header(
    owner: User,
    portfolio: Portfolio,
) -> None:
    response = authenticated_client(owner).post(
        reverse(
            "api-v1-portfolio-transaction-import-preview",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"csv_text": "type,date\nDEPOSIT,2026-09-15\n"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "CSV_HEADER_INVALID"


@pytest.mark.django_db
def test_import_rejects_file_byte_limit(
    owner: User,
    portfolio: Portfolio,
) -> None:
    content = "x" * (MAX_TRANSACTION_IMPORT_BYTES + 1)

    response = authenticated_client(owner).post(
        reverse(
            "api-v1-portfolio-transaction-import-preview",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"csv_text": content},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    # The transport max-length or application byte limit may reject first.
    assert response.data["code"] in {"VALIDATION_ERROR", "CSV_TOO_LARGE"}


@pytest.mark.django_db
def test_import_rejects_row_limit(
    owner: User,
    portfolio: Portfolio,
) -> None:
    header = "transaction_type,occurred_at,asset_id,quantity,price,fees,cash_amount\n"
    rows = "".join(
        f"DEPOSIT,2026-09-15T14:{index % 60:02d}:00Z,,,,0,1.00\n"
        for index in range(MAX_TRANSACTION_IMPORT_ROWS + 1)
    )

    response = authenticated_client(owner).post(
        reverse(
            "api-v1-portfolio-transaction-import-preview",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"csv_text": header + rows},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "CSV_TOO_MANY_ROWS"


@pytest.mark.django_db
def test_cross_user_import_is_hidden() -> None:
    owner = User.objects.create_user(
        email="csv-private-owner@example.com",
        password="test-password-123",
    )
    attacker = User.objects.create_user(
        email="csv-private-attacker@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(user=owner, name="Private")

    response = authenticated_client(attacker).post(
        reverse(
            "api-v1-portfolio-transaction-import-preview",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "csv_text": (
                "transaction_type,occurred_at,asset_id,quantity,price,fees,cash_amount\n"
                "DEPOSIT,2026-09-15T14:00:00Z,,,,0,1.00\n"
            )
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert Transaction.objects.count() == 0


def install_symbol_resolution(
    monkeypatch: pytest.MonkeyPatch,
    *,
    symbol: str,
    asset_id: UUID | None,
) -> None:
    monkeypatch.setattr(
        "apps.portfolios.api.management_views.load_market_data_provider_configuration",
        lambda: SimpleNamespace(default_provider="yfinance"),
    )
    monkeypatch.setattr(
        "apps.portfolios.api.management_views.resolve_canonical_assets_with_discovery",
        lambda symbols, **_kwargs: CanonicalAssetResolutionBatch(
            provider="yfinance",
            outcomes=(
                CanonicalAssetResolutionOutcome(
                    symbol=symbol,
                    status=(
                        CanonicalAssetResolutionStatus.RESOLVED
                        if asset_id is not None
                        else CanonicalAssetResolutionStatus.NOT_FOUND
                    ),
                    asset_id=asset_id,
                ),
            ),
        ),
    )
    monkeypatch.setattr(
        "apps.portfolios.api.management_views.get_asset_resolver",
        lambda: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "apps.portfolios.api.management_views.get_asset_discovery_provider",
        lambda _provider_name: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "apps.portfolios.api.management_views.get_asset_catalog_writer",
        lambda: SimpleNamespace(),
    )


@pytest.mark.django_db
def test_preview_resolves_user_friendly_ticker_csv_to_canonical_asset(
    monkeypatch: pytest.MonkeyPatch,
    owner: User,
    portfolio: Portfolio,
    asset: Asset,
) -> None:
    install_symbol_resolution(
        monkeypatch,
        symbol="AAPL",
        asset_id=asset.id,
    )
    content = (
        "transaction_type,occurred_at,asset_symbol,quantity,price,fees,cash_amount\n"
        "DEPOSIT,2026-09-15T13:00:00Z,,,,0,1000.00\n"
        "BUY,2026-09-15T14:00:00Z,aapl,2,100,1,\n"
    )

    response = authenticated_client(owner).post(
        reverse(
            "api-v1-portfolio-transaction-import-preview",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"csv_text": content},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["can_import"] is True
    buy_row = response.data["rows"][1]
    assert buy_row["asset_symbol"] == "AAPL"
    assert buy_row["asset_id"] == str(asset.id)
    assert Transaction.objects.count() == 0


@pytest.mark.django_db
def test_ticker_csv_reports_unresolved_symbol_without_substitution(
    monkeypatch: pytest.MonkeyPatch,
    owner: User,
    portfolio: Portfolio,
) -> None:
    install_symbol_resolution(
        monkeypatch,
        symbol="UNKNOWN",
        asset_id=None,
    )
    content = (
        "transaction_type,occurred_at,asset_symbol,quantity,price,fees,cash_amount\n"
        "BUY,2026-09-15T14:00:00Z,UNKNOWN,1,100,0,\n"
    )

    response = authenticated_client(owner).post(
        reverse(
            "api-v1-portfolio-transaction-import-preview",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"csv_text": content},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["can_import"] is False
    row = response.data["rows"][0]
    assert row["asset_symbol"] == "UNKNOWN"
    assert row["asset_id"] is None
    assert row["issues"] == [
        {
            "code": "ASSET_NOT_FOUND",
            "field": "asset_symbol",
            "message": (
                "Ticker UNKNOWN could not be resolved to a supported canonical USD stock or ETF."
            ),
        }
    ]
    assert Transaction.objects.count() == 0


@pytest.mark.django_db
def test_confirm_ticker_csv_persists_resolved_canonical_asset_atomically(
    monkeypatch: pytest.MonkeyPatch,
    owner: User,
    portfolio: Portfolio,
    asset: Asset,
) -> None:
    install_symbol_resolution(
        monkeypatch,
        symbol="AAPL",
        asset_id=asset.id,
    )
    content = (
        "transaction_type,occurred_at,asset_symbol,quantity,price,fees,cash_amount\n"
        "DEPOSIT,2026-09-15T13:00:00Z,,,,0,1000.00\n"
        "BUY,2026-09-15T14:00:00Z,AAPL,2,100,1,\n"
    )

    response = authenticated_client(owner).post(
        reverse(
            "api-v1-portfolio-transaction-import-confirm",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"csv_text": content},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["imported_count"] == 2
    assert Transaction.objects.filter(portfolio=portfolio).count() == 2
    buy = Transaction.objects.get(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
    )
    assert buy.asset_id == asset.id
