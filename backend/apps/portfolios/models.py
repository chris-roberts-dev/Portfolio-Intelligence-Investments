"""Canonical portfolio and transaction-ledger persistence models.

Development guide references: Sections 8.1, 8.5, 8.6, 8.7, and 10.1-10.3.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.portfolios.querysets import PortfolioManager, TransactionManager


class TransactionType(models.TextChoices):
    """Supported MVP transaction-ledger event types."""

    DEPOSIT = "DEPOSIT", "Deposit"
    WITHDRAWAL = "WITHDRAWAL", "Withdrawal"
    BUY = "BUY", "Buy"
    SELL = "SELL", "Sell"
    DIVIDEND = "DIVIDEND", "Dividend"


class Portfolio(models.Model):
    """User-owned USD portfolio with an optional benchmark asset."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolios",
    )
    name = models.CharField(max_length=255)
    base_currency = models.CharField(max_length=3, default="USD")
    benchmark_asset = models.ForeignKey(
        "assets.Asset",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="benchmark_portfolios",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PortfolioManager()

    class Meta:
        ordering = ("created_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(base_currency="USD"),
                name="portfolio_base_currency_usd",
            ),
            models.CheckConstraint(
                condition=~Q(name=""),
                name="portfolio_name_nonblank",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Transaction(models.Model):
    """One authoritative transaction-ledger event for an owned portfolio."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    transaction_type = models.CharField(
        max_length=16,
        choices=TransactionType.choices,
    )
    asset = models.ForeignKey(
        "assets.Asset",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ledger_transactions",
    )
    occurred_at = models.DateTimeField()
    source_sequence = models.PositiveBigIntegerField(default=0)
    quantity = models.DecimalField(
        max_digits=28,
        decimal_places=12,
        null=True,
        blank=True,
    )
    price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
    )
    fees = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal("0"),
    )
    cash_amount = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TransactionManager()

    class Meta:
        ordering = ("occurred_at", "source_sequence", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(fees__gte=0),
                name="transaction_fees_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        transaction_type__in=(
                            TransactionType.DEPOSIT,
                            TransactionType.WITHDRAWAL,
                        ),
                        cash_amount__isnull=False,
                        cash_amount__gt=0,
                        asset__isnull=True,
                        quantity__isnull=True,
                        price__isnull=True,
                    )
                    | Q(
                        transaction_type__in=(
                            TransactionType.BUY,
                            TransactionType.SELL,
                        ),
                        asset__isnull=False,
                        quantity__isnull=False,
                        quantity__gt=0,
                        price__isnull=False,
                        price__gt=0,
                        cash_amount__isnull=True,
                    )
                    | (
                        Q(
                            transaction_type=TransactionType.DIVIDEND,
                            asset__isnull=False,
                            cash_amount__isnull=False,
                            cash_amount__gt=0,
                        )
                        & (Q(quantity__isnull=True) | Q(quantity__gt=0))
                        & (Q(price__isnull=True) | Q(price__gt=0))
                    )
                ),
                name="transaction_fields_match_type",
            ),
            models.UniqueConstraint(
                fields=("portfolio", "occurred_at", "source_sequence"),
                name="transaction_portfolio_time_sequence_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.transaction_type} {self.occurred_at.isoformat()}"

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}

        if self.occurred_at is not None and timezone.is_naive(self.occurred_at):
            errors["occurred_at"] = "occurred_at must be timezone-aware."

        if self.fees is not None and self.fees < 0:
            errors["fees"] = "fees must be greater than or equal to zero."

        if self.transaction_type in (
            TransactionType.DEPOSIT,
            TransactionType.WITHDRAWAL,
        ):
            if self.cash_amount is None or self.cash_amount <= 0:
                errors["cash_amount"] = "cash_amount must be greater than zero."
            if self.asset_id is not None:
                errors["asset"] = "asset must be absent for cash-flow transactions."
            if self.quantity is not None:
                errors["quantity"] = "quantity must be absent for cash-flow transactions."
            if self.price is not None:
                errors["price"] = "price must be absent for cash-flow transactions."

        elif self.transaction_type in (
            TransactionType.BUY,
            TransactionType.SELL,
        ):
            if self.asset_id is None:
                errors["asset"] = "asset is required for BUY and SELL transactions."
            if self.quantity is None or self.quantity <= 0:
                errors["quantity"] = "quantity must be greater than zero."
            if self.price is None or self.price <= 0:
                errors["price"] = "price must be greater than zero."
            if self.cash_amount is not None:
                errors["cash_amount"] = "cash_amount must be absent for BUY and SELL transactions."

        elif self.transaction_type == TransactionType.DIVIDEND:
            if self.asset_id is None:
                errors["asset"] = "asset is required for DIVIDEND transactions."
            if self.cash_amount is None or self.cash_amount <= 0:
                errors["cash_amount"] = "cash_amount must be greater than zero."
            if self.quantity is not None and self.quantity <= 0:
                errors["quantity"] = "quantity must be greater than zero when supplied."
            if self.price is not None and self.price <= 0:
                errors["price"] = "price must be greater than zero when supplied."

        else:
            errors["transaction_type"] = "Unsupported transaction type."

        if errors:
            raise ValidationError(errors)
