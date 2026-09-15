"""Canonical persisted asset identity models.

Development guide reference: Sections 8.1 and 8.2.
"""

from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class AssetType(models.TextChoices):
    """Supported MVP security types."""

    STOCK = "STOCK", "Stock"
    ETF = "ETF", "ETF"


class Asset(models.Model):
    """Canonical internal security identity used by the application."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    symbol = models.CharField(max_length=32)
    name = models.CharField(max_length=255)
    asset_type = models.CharField(max_length=16, choices=AssetType.choices)
    exchange = models.CharField(max_length=64)
    currency = models.CharField(max_length=3, default="USD")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("symbol", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(asset_type__in=(AssetType.STOCK, AssetType.ETF)),
                name="asset_type_supported",
            ),
            models.CheckConstraint(
                condition=Q(currency="USD"),
                name="asset_currency_usd",
            ),
            models.CheckConstraint(
                condition=~Q(symbol=""),
                name="asset_symbol_nonblank",
            ),
            models.CheckConstraint(
                condition=~Q(name=""),
                name="asset_name_nonblank",
            ),
            models.CheckConstraint(
                condition=~Q(exchange=""),
                name="asset_exchange_nonblank",
            ),
        ]

    def __str__(self) -> str:
        return self.symbol


class AssetProviderSymbol(models.Model):
    """Provider-specific symbol mapped to one canonical internal asset."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="provider_symbols",
    )
    provider = models.CharField(max_length=32)
    provider_symbol = models.CharField(max_length=64)
    is_primary = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("provider", "provider_symbol", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("provider", "provider_symbol"),
                name="asset_provider_identity_uniq",
            ),
            models.CheckConstraint(
                condition=~Q(provider=""),
                name="asset_provider_nonblank",
            ),
            models.CheckConstraint(
                condition=~Q(provider_symbol=""),
                name="asset_provider_symbol_nonblank",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.provider_symbol}"

    def clean(self) -> None:
        super().clean()

        if self.verified_at is not None and timezone.is_naive(self.verified_at):
            raise ValidationError({"verified_at": "verified_at must be timezone-aware."})
