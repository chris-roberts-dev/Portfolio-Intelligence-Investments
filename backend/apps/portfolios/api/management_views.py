"""Authenticated asset catalog and owned-portfolio transaction mutation APIs."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.models import User
from apps.assets.models import Asset
from apps.portfolios.api.contracts import PortfolioApiErrorSerializer
from apps.portfolios.api.management_serializers import (
    AssetCatalogItemSerializer,
    PortfolioTransactionCreateRequestSerializer,
    PortfolioTransactionSerializer,
    TransactionImportErrorSerializer,
    TransactionImportPreviewSerializer,
    TransactionImportRequestSerializer,
    TransactionImportResultSerializer,
    TransactionWriteValidationErrorSerializer,
)
from apps.portfolios.models import Portfolio
from apps.portfolios.services.transaction_ingestion import (
    TransactionImportFileError,
    TransactionImportValidationError,
    TransactionWriteError,
    create_portfolio_transaction,
    import_transaction_csv,
    preview_transaction_csv,
)


@extend_schema(
    operation_id="asset_catalog_list",
    description=(
        "List active canonical USD stock/ETF identities available for transaction entry. "
        "This endpoint performs no provider lookup."
    ),
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            response=AssetCatalogItemSerializer(many=True),
            description="Active canonical asset identities.",
        ),
    },
    tags=["assets"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def asset_catalog_view(request: Request) -> Response:
    """Return active canonical assets without provider-side symbol substitution."""
    assets = Asset.objects.filter(
        is_active=True,
        currency="USD",
    ).order_by("symbol", "id")

    return Response(
        AssetCatalogItemSerializer(
            cast(Any, assets),
            many=True,
        ).data,
        status=status.HTTP_200_OK,
    )


@extend_schema(
    operation_id="portfolio_transaction_create",
    description=(
        "Create one canonical owned-portfolio ledger transaction and replay the "
        "authoritative long-only ledger before commit."
    ),
    request=PortfolioTransactionCreateRequestSerializer,
    responses={
        status.HTTP_201_CREATED: OpenApiResponse(
            response=PortfolioTransactionSerializer,
            description="Persisted canonical transaction.",
        ),
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(
            response=TransactionWriteValidationErrorSerializer,
            description="Transaction input or ledger replay validation failed.",
        ),
        status.HTTP_404_NOT_FOUND: OpenApiResponse(
            response=PortfolioApiErrorSerializer,
            description="The portfolio does not exist in the authenticated user's scope.",
        ),
    },
    tags=["transactions"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def portfolio_transaction_create_view(
    request: Request,
    portfolio_id: UUID,
) -> Response:
    """Validate and commit one transaction to an owner-scoped portfolio."""
    user = cast(User, request.user)
    portfolio = _owned_portfolio(user, portfolio_id)

    if portfolio is None:
        return _portfolio_not_found_response()

    serializer = PortfolioTransactionCreateRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return _validation_response(serializer.errors)

    try:
        ledger_entry = create_portfolio_transaction(
            portfolio,
            serializer.transaction_input,
        )
    except TransactionWriteError as exc:
        return Response(
            {
                "code": exc.code.value,
                "errors": exc.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        PortfolioTransactionSerializer(ledger_entry).data,
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    operation_id="portfolio_transaction_import_preview",
    description=(
        "Parse and validate the documented CSV transaction format without persisting "
        "rows. Preview uses the same transaction model validation and ledger replay "
        "rules as confirmation."
    ),
    request=TransactionImportRequestSerializer,
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            response=TransactionImportPreviewSerializer,
            description="Normalized atomic-import preview.",
        ),
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(
            response=TransactionImportErrorSerializer,
            description="CSV request, structure, or bounds validation failed.",
        ),
        status.HTTP_404_NOT_FOUND: OpenApiResponse(
            response=PortfolioApiErrorSerializer,
            description="The portfolio does not exist in the authenticated user's scope.",
        ),
    },
    tags=["transactions"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def portfolio_transaction_import_preview_view(
    request: Request,
    portfolio_id: UUID,
) -> Response:
    """Return a non-persisting normalized CSV preview."""
    user = cast(User, request.user)
    portfolio = _owned_portfolio(user, portfolio_id)

    if portfolio is None:
        return _portfolio_not_found_response()

    serializer = TransactionImportRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return _validation_response(serializer.errors)

    try:
        preview = preview_transaction_csv(
            portfolio,
            serializer.csv_text_value,
        )
    except TransactionImportFileError as exc:
        return _import_file_error_response(exc)

    return Response(
        TransactionImportPreviewSerializer(preview).data,
        status=status.HTTP_200_OK,
    )


@extend_schema(
    operation_id="portfolio_transaction_import_confirm",
    description=(
        "Re-parse, revalidate, replay, and atomically commit the documented CSV "
        "transaction format. Any invalid row prevents the complete import."
    ),
    request=TransactionImportRequestSerializer,
    responses={
        status.HTTP_201_CREATED: OpenApiResponse(
            response=TransactionImportResultSerializer,
            description="Committed atomic CSV import.",
        ),
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(
            response=TransactionImportErrorSerializer,
            description="CSV structure, row validation, or ledger replay validation failed.",
        ),
        status.HTTP_404_NOT_FOUND: OpenApiResponse(
            response=PortfolioApiErrorSerializer,
            description="The portfolio does not exist in the authenticated user's scope.",
        ),
    },
    tags=["transactions"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def portfolio_transaction_import_confirm_view(
    request: Request,
    portfolio_id: UUID,
) -> Response:
    """Atomically commit a CSV only after complete revalidation."""
    user = cast(User, request.user)
    portfolio = _owned_portfolio(user, portfolio_id)

    if portfolio is None:
        return _portfolio_not_found_response()

    serializer = TransactionImportRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return _validation_response(serializer.errors)

    try:
        result = import_transaction_csv(
            portfolio,
            serializer.csv_text_value,
        )
    except TransactionImportFileError as exc:
        return _import_file_error_response(exc)
    except TransactionImportValidationError as exc:
        return Response(
            {
                "code": "IMPORT_VALIDATION_FAILED",
                "detail": str(exc),
                "preview": TransactionImportPreviewSerializer(exc.preview).data,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        TransactionImportResultSerializer(result).data,
        status=status.HTTP_201_CREATED,
    )


def _owned_portfolio(
    user: User,
    portfolio_id: UUID,
) -> Portfolio | None:
    return Portfolio.objects.owned_by(user).filter(id=portfolio_id).first()


def _portfolio_not_found_response() -> Response:
    return Response(
        {
            "code": "PORTFOLIO_NOT_FOUND",
            "detail": "Portfolio was not found.",
        },
        status=status.HTTP_404_NOT_FOUND,
    )


def _validation_response(errors: object) -> Response:
    return Response(
        {
            "code": "VALIDATION_ERROR",
            "errors": errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def _import_file_error_response(exc: TransactionImportFileError) -> Response:
    return Response(
        {
            "code": exc.code.value,
            "detail": str(exc),
        },
        status=status.HTTP_400_BAD_REQUEST,
    )
