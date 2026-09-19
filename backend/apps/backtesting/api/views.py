"""Thin authenticated DRF views for persisted Phase 6 backtest runs."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.models import User
from apps.backtesting.api.serializers import (
    BacktestApiErrorSerializer,
    BacktestRunCreateRequestSerializer,
    BacktestRunSerializer,
    BacktestValidationErrorSerializer,
)
from apps.backtesting.models import BacktestRun
from apps.backtesting.services import BacktestApplicationError, create_backtest_run
from apps.market_data.providers.configuration import (
    ProviderConfigurationError,
    load_market_data_provider_configuration,
    resolve_market_data_provider,
)
from apps.market_data.providers.registry import ProviderRegistryError
from apps.market_data.services.market_bar_query import execute_market_bar_query
from apps.portfolios.api.dependencies import get_asset_resolver


@extend_schema_view(
    get=extend_schema(
        operation_id="backtest_run_list",
        description="List persisted backtest runs owned by the authenticated user.",
        responses={status.HTTP_200_OK: BacktestRunSerializer(many=True)},
        tags=["backtesting"],
    ),
    post=extend_schema(
        operation_id="backtest_run_create",
        description=(
            "Create and synchronously execute one persisted deterministic buy-and-hold "
            "backtest. Expected analytical failures remain auditable as FAILED run resources."
        ),
        request=BacktestRunCreateRequestSerializer,
        responses={
            status.HTTP_201_CREATED: BacktestRunSerializer,
            status.HTTP_400_BAD_REQUEST: BacktestValidationErrorSerializer,
            status.HTTP_503_SERVICE_UNAVAILABLE: BacktestApiErrorSerializer,
        },
        tags=["backtesting"],
    ),
)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def backtest_run_list_view(request: Request) -> Response:
    """List owned runs or create one owner-scoped synchronous run."""
    user = cast(User, request.user)

    if request.method == "GET":
        queryset = BacktestRun.objects.filter(user=user).order_by("-created_at", "id")
        return Response(
            BacktestRunSerializer(cast(Any, queryset), many=True).data,
            status=status.HTTP_200_OK,
        )

    serializer = BacktestRunCreateRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"code": "VALIDATION_ERROR", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        configuration = load_market_data_provider_configuration()
        provider = resolve_market_data_provider(configuration=configuration)
    except (ProviderConfigurationError, ProviderRegistryError) as exc:
        return Response(
            {"code": "PROVIDER_CONFIGURATION_ERROR", "detail": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        run = create_backtest_run(
            user=user,
            command=serializer.to_command(),
            provider_name=configuration.default_provider,
            resolver=get_asset_resolver(),
            provider=provider,
            executor=execute_market_bar_query,
        )
    except BacktestApplicationError as exc:
        return Response(
            {"code": "VALIDATION_ERROR", "errors": {"non_field_errors": [str(exc)]}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(BacktestRunSerializer(run).data, status=status.HTTP_201_CREATED)


@extend_schema(
    operation_id="backtest_run_detail",
    description="Return one backtest run owned by the authenticated user.",
    responses={
        status.HTTP_200_OK: BacktestRunSerializer,
        status.HTTP_404_NOT_FOUND: OpenApiResponse(
            response=BacktestApiErrorSerializer,
            description="Run does not exist in the authenticated user's scope.",
        ),
    },
    tags=["backtesting"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def backtest_run_detail_view(request: Request, run_id: UUID) -> Response:
    """Return one owner-scoped run without cross-user disclosure."""
    user = cast(User, request.user)
    run = BacktestRun.objects.filter(user=user, id=run_id).first()
    if run is None:
        return Response(
            {"code": "NOT_FOUND", "detail": "Backtest run not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(BacktestRunSerializer(run).data, status=status.HTTP_200_OK)
