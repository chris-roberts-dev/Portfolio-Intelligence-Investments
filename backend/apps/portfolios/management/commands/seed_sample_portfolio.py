"""Seed the deterministic v0.1 sample portfolio used by demos and Playwright.

The command persists only canonical application models. Market prices remain in
committed CSV fixtures and are consumed through the normal provider boundary.
No portfolio metric is precomputed or stored by this command.
"""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.assets.models import Asset, AssetProviderSymbol, AssetType
from apps.portfolios.models import Portfolio, Transaction, TransactionType
from apps.portfolios.services.ledger import replay_portfolio_ledger

SAMPLE_USER_EMAIL = "sample.portfolio@example.test"
SAMPLE_USER_PASSWORD = "local-demo-password"
SAMPLE_PORTFOLIO_ID = UUID("00000000-0000-0000-0000-00000000d001")
SAMPLE_AAPL_ID = UUID("00000000-0000-0000-0000-00000000a101")
SAMPLE_MSFT_ID = UUID("00000000-0000-0000-0000-00000000a102")
SAMPLE_SPY_ID = UUID("00000000-0000-0000-0000-00000000a103")
SAMPLE_NODATA_ID = UUID("00000000-0000-0000-0000-00000000a104")
VERIFIED_AT = datetime(2026, 1, 2, 13, 0, tzinfo=UTC)


class Command(BaseCommand):
    help = "Create or refresh the deterministic offline v0.1 sample portfolio."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Delete existing portfolios owned by the sample user before "
                "recreating the canonical sample workflow."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        user, _ = User.objects.get_or_create(
            email=SAMPLE_USER_EMAIL,
            defaults={
                "first_name": "Sample",
                "last_name": "Investor",
                "is_active": True,
            },
        )
        user.first_name = "Sample"
        user.last_name = "Investor"
        user.is_active = True
        user.set_password(SAMPLE_USER_PASSWORD)
        user.full_clean()
        user.save()

        if options["reset"]:
            Portfolio.objects.filter(user=user).delete()

        aapl = _upsert_asset(
            asset_id=SAMPLE_AAPL_ID,
            symbol="AAPL",
            name="Apple Inc.",
            asset_type=AssetType.STOCK,
            exchange="NASDAQ",
        )
        msft = _upsert_asset(
            asset_id=SAMPLE_MSFT_ID,
            symbol="MSFT",
            name="Microsoft Corporation",
            asset_type=AssetType.STOCK,
            exchange="NASDAQ",
        )
        spy = _upsert_asset(
            asset_id=SAMPLE_SPY_ID,
            symbol="SPY",
            name="SPDR S&P 500 ETF Trust",
            asset_type=AssetType.ETF,
            exchange="NYSEARCA",
        )
        nodata = _upsert_asset(
            asset_id=SAMPLE_NODATA_ID,
            symbol="NODATA",
            name="No Data Fixture",
            asset_type=AssetType.ETF,
            exchange="NYSEARCA",
        )

        for asset in (aapl, msft, spy, nodata):
            AssetProviderSymbol.objects.update_or_create(
                provider="csv",
                provider_symbol=asset.symbol,
                defaults={
                    "asset": asset,
                    "is_primary": True,
                    "verified_at": VERIFIED_AT,
                },
            )

        portfolio, _ = Portfolio.objects.update_or_create(
            id=SAMPLE_PORTFOLIO_ID,
            defaults={
                "user": user,
                "name": "Deterministic Sample Portfolio",
                "base_currency": "USD",
                "benchmark_asset": spy,
            },
        )
        portfolio.user = user
        portfolio.name = "Deterministic Sample Portfolio"
        portfolio.base_currency = "USD"
        portfolio.benchmark_asset = spy
        portfolio.full_clean()
        portfolio.save()

        Transaction.objects.filter(portfolio=portfolio).delete()
        transactions = (
            _transaction(
                portfolio=portfolio,
                transaction_type=TransactionType.DEPOSIT,
                occurred_at=datetime(2026, 1, 2, 14, 0, tzinfo=UTC),
                source_sequence=1,
                cash_amount=Decimal("100000.00"),
            ),
            _transaction(
                portfolio=portfolio,
                transaction_type=TransactionType.BUY,
                occurred_at=datetime(2026, 1, 5, 15, 0, tzinfo=UTC),
                source_sequence=2,
                asset=aapl,
                quantity=Decimal("100"),
                price=Decimal("101.25"),
                fees=Decimal("1.00"),
            ),
            _transaction(
                portfolio=portfolio,
                transaction_type=TransactionType.BUY,
                occurred_at=datetime(2026, 1, 5, 15, 5, tzinfo=UTC),
                source_sequence=3,
                asset=msft,
                quantity=Decimal("80"),
                price=Decimal("202.50"),
                fees=Decimal("1.00"),
            ),
            _transaction(
                portfolio=portfolio,
                transaction_type=TransactionType.DIVIDEND,
                occurred_at=datetime(2026, 4, 1, 14, 0, tzinfo=UTC),
                source_sequence=4,
                asset=aapl,
                cash_amount=Decimal("150.00"),
            ),
            _transaction(
                portfolio=portfolio,
                transaction_type=TransactionType.DEPOSIT,
                occurred_at=datetime(2026, 6, 1, 14, 0, tzinfo=UTC),
                source_sequence=5,
                cash_amount=Decimal("10000.00"),
            ),
            _transaction(
                portfolio=portfolio,
                transaction_type=TransactionType.SELL,
                occurred_at=datetime(2026, 7, 1, 15, 0, tzinfo=UTC),
                source_sequence=6,
                asset=aapl,
                quantity=Decimal("10"),
                price=Decimal("132.00"),
                fees=Decimal("1.00"),
            ),
            _transaction(
                portfolio=portfolio,
                transaction_type=TransactionType.BUY,
                occurred_at=datetime(2026, 8, 3, 15, 0, tzinfo=UTC),
                source_sequence=7,
                asset=msft,
                quantity=Decimal("10"),
                price=Decimal("239.00"),
                fees=Decimal("1.00"),
            ),
        )

        Transaction.objects.bulk_create(transactions)
        replay = replay_portfolio_ledger(portfolio)

        self.stdout.write(self.style.SUCCESS("Deterministic sample portfolio is ready."))
        self.stdout.write(f"email={SAMPLE_USER_EMAIL}")
        self.stdout.write(f"password={SAMPLE_USER_PASSWORD}")
        self.stdout.write(f"portfolio_id={portfolio.id}")
        self.stdout.write(f"transactions={replay.transaction_count}")
        self.stdout.write("provider=csv")


def _upsert_asset(
    *,
    asset_id: UUID,
    symbol: str,
    name: str,
    asset_type: AssetType,
    exchange: str,
) -> Asset:
    asset, _ = Asset.objects.update_or_create(
        id=asset_id,
        defaults={
            "symbol": symbol,
            "name": name,
            "asset_type": asset_type,
            "exchange": exchange,
            "currency": "USD",
            "is_active": True,
        },
    )
    asset.full_clean()
    asset.save()
    return asset


def _transaction(
    *,
    portfolio: Portfolio,
    transaction_type: TransactionType,
    occurred_at: datetime,
    source_sequence: int,
    asset: Asset | None = None,
    quantity: Decimal | None = None,
    price: Decimal | None = None,
    fees: Decimal = Decimal("0"),
    cash_amount: Decimal | None = None,
) -> Transaction:
    entry = Transaction(
        portfolio=portfolio,
        transaction_type=transaction_type,
        asset=asset,
        occurred_at=occurred_at,
        source_sequence=source_sequence,
        quantity=quantity,
        price=price,
        fees=fees,
        cash_amount=cash_amount,
    )
    entry.full_clean()
    return entry
