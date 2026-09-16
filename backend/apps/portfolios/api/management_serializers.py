"""DRF transport contracts for portfolio management and transaction ingestion."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from rest_framework import serializers

from apps.assets.models import Asset
from apps.portfolios.models import Transaction, TransactionType
from apps.portfolios.services.transaction_ingestion import (
    MAX_TRANSACTION_IMPORT_BYTES,
    TransactionImportIssue,
    TransactionImportIssueCode,
    TransactionImportPreview,
    TransactionImportResult,
    TransactionWriteInput,
)


class PortfolioCreateRequestSerializer(serializers.Serializer[object]):
    """Create one authenticated-user-owned USD portfolio."""

    name = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
        allow_blank=False,
    )

    @property
    def name_value(self) -> str:
        return cast(str, self.validated_data["name"])


class PortfolioRenameRequestSerializer(serializers.Serializer[object]):
    """Rename one authenticated-user-owned portfolio."""

    name = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
        allow_blank=False,
    )

    @property
    def name_value(self) -> str:
        return cast(str, self.validated_data["name"])


class PortfolioBenchmarkRequestSerializer(serializers.Serializer[object]):
    """Select or clear one canonical benchmark asset for an owned portfolio."""

    benchmark_asset_id = serializers.UUIDField(allow_null=True)

    @property
    def benchmark_asset_id_value(self) -> UUID | None:
        return cast(UUID | None, self.validated_data["benchmark_asset_id"])


class AssetCatalogItemSerializer(serializers.Serializer[Asset]):
    """Canonical active asset identity available for transaction entry."""

    id = serializers.UUIDField(read_only=True)
    symbol = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    asset_type = serializers.CharField(read_only=True)
    exchange = serializers.CharField(read_only=True)
    currency = serializers.CharField(read_only=True)


class PortfolioTransactionSerializer(serializers.Serializer[Transaction]):
    """Persisted canonical transaction representation."""

    id = serializers.UUIDField(read_only=True)
    portfolio_id = serializers.UUIDField(read_only=True)
    transaction_type = serializers.CharField(read_only=True)
    asset_id = serializers.UUIDField(read_only=True, allow_null=True)
    asset_symbol = serializers.CharField(
        source="asset.symbol",
        read_only=True,
        allow_null=True,
    )
    occurred_at = serializers.DateTimeField(read_only=True)
    source_sequence = serializers.IntegerField(read_only=True)
    quantity = serializers.CharField(read_only=True, allow_null=True)
    price = serializers.CharField(read_only=True, allow_null=True)
    fees = serializers.CharField(read_only=True)
    cash_amount = serializers.CharField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)


class PortfolioTransactionCreateRequestSerializer(serializers.Serializer[object]):
    """Transport validation for one canonical ledger transaction."""

    transaction_type = serializers.ChoiceField(choices=TransactionType.values)
    occurred_at = serializers.DateTimeField()
    asset_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    quantity = serializers.DecimalField(
        max_digits=28,
        decimal_places=12,
        required=False,
        allow_null=True,
    )
    price = serializers.DecimalField(
        max_digits=20,
        decimal_places=8,
        required=False,
        allow_null=True,
    )
    fees = serializers.DecimalField(
        max_digits=20,
        decimal_places=8,
        required=False,
        default=Decimal("0"),
    )
    cash_amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=8,
        required=False,
        allow_null=True,
    )

    @property
    def transaction_input(self) -> TransactionWriteInput:
        """Return the normalized application-layer write input."""
        return TransactionWriteInput(
            transaction_type=TransactionType(cast(str, self.validated_data["transaction_type"])),
            occurred_at=self.validated_data["occurred_at"],
            asset_id=self.validated_data.get("asset_id"),
            quantity=self.validated_data.get("quantity"),
            price=self.validated_data.get("price"),
            fees=cast(Decimal, self.validated_data["fees"]),
            cash_amount=self.validated_data.get("cash_amount"),
        )


class TransactionWriteValidationErrorSerializer(serializers.Serializer[object]):
    """Stable transaction-write validation response."""

    code = serializers.CharField(read_only=True)
    errors = cast(
        Any,
        serializers.DictField(
            child=serializers.ListField(child=serializers.CharField()),
            read_only=True,
        ),
    )


class TransactionImportRequestSerializer(serializers.Serializer[object]):
    """Bounded CSV-text request used by both preview and confirm."""

    csv_text = serializers.CharField(
        trim_whitespace=False,
        max_length=MAX_TRANSACTION_IMPORT_BYTES,
    )

    @property
    def csv_text_value(self) -> str:
        return cast(str, self.validated_data["csv_text"])


class TransactionImportIssueSerializer(serializers.Serializer[TransactionImportIssue]):
    """One stable per-row CSV validation issue."""

    code = serializers.ChoiceField(
        choices=[code.value for code in TransactionImportIssueCode],
        read_only=True,
    )
    field = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)


class TransactionImportRowPreviewSerializer(serializers.Serializer[object]):
    """One normalized CSV row preview."""

    row_number = serializers.IntegerField(read_only=True)
    valid = serializers.BooleanField(read_only=True)
    transaction_type = serializers.CharField(read_only=True, allow_null=True)
    occurred_at = serializers.CharField(read_only=True, allow_null=True)
    asset_id = serializers.CharField(read_only=True, allow_null=True)
    asset_symbol = serializers.CharField(read_only=True, allow_null=True)
    quantity = serializers.CharField(read_only=True, allow_null=True)
    price = serializers.CharField(read_only=True, allow_null=True)
    fees = serializers.CharField(read_only=True, allow_null=True)
    cash_amount = serializers.CharField(read_only=True, allow_null=True)
    issues = TransactionImportIssueSerializer(many=True, read_only=True)


class TransactionImportPreviewSerializer(serializers.Serializer[TransactionImportPreview]):
    """Atomic CSV import preview contract."""

    row_count = serializers.IntegerField(read_only=True)
    valid_count = serializers.IntegerField(read_only=True)
    invalid_count = serializers.IntegerField(read_only=True)
    can_import = serializers.BooleanField(read_only=True)
    atomic = serializers.BooleanField(read_only=True)
    rows = TransactionImportRowPreviewSerializer(many=True, read_only=True)


class TransactionImportResultSerializer(serializers.Serializer[TransactionImportResult]):
    """Successful atomic CSV import result."""

    imported_count = serializers.IntegerField(read_only=True)
    transactions = PortfolioTransactionSerializer(many=True, read_only=True)


class TransactionImportErrorSerializer(serializers.Serializer[object]):
    """Stable CSV request/file/confirm validation response envelope."""

    code = serializers.CharField(read_only=True)
    detail = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    errors = cast(
        Any,
        serializers.DictField(
            child=serializers.ListField(child=serializers.CharField()),
            read_only=True,
        ),
    )
    preview = TransactionImportPreviewSerializer(
        read_only=True,
    )
