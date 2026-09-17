"""Thin authenticated DRF views for persisted optimization-run resources."""

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
from apps.market_data.providers.configuration import (
    ProviderConfigurationError,
    load_market_data_provider_configuration,
    resolve_market_data_provider,
)
from apps.market_data.providers.registry import ProviderRegistryError
from apps.market_data.services.market_bar_query import execute_market_bar_query
from apps.optimization.api.serializers import (
    OptimizationApiErrorSerializer,
    OptimizationRunCreateRequestSerializer,
    OptimizationRunSerializer,
    OptimizationValidationErrorSerializer,
)
from apps.optimization.models import OptimizationRun
from apps.optimization.services import (
    OptimizationApplicationError,
    create_optimization_run,
)
from apps.portfolios.api.dependencies import get_asset_resolver
from apps.portfolios.models import Portfolio


@extend_schema_view(
    get=extend_schema(
        operation_id="optimization_run_list",
        description="List optimization runs owned by the authenticated user.",
        responses={status.HTTP_200_OK: OptimizationRunSerializer(many=True)},
        tags=["optimization"],
    ),
    post=extend_schema(
        operation_id="optimization_run_create",
        description=(
            "Create and synchronously execute one persisted historical optimization run. "
            "Failed domain/solver executions remain auditable as FAILED run resources."
        ),
        request=OptimizationRunCreateRequestSerializer,
        responses={
            status.HTTP_201_CREATED: OptimizationRunSerializer,
            status.HTTP_400_BAD_REQUEST: OptimizationValidationErrorSerializer,
            status.HTTP_404_NOT_FOUND: OptimizationApiErrorSerializer,
            status.HTTP_503_SERVICE_UNAVAILABLE: OptimizationApiErrorSerializer,
        },
        tags=["optimization"],
    ),
)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def optimization_run_list_view(request: Request) -> Response:
    """List owned runs or create one owner-scoped synchronous run."""
    user = cast(User, request.user)

    if request.method == "GET":
        queryset = (
            OptimizationRun.objects.filter(user=user)
            .select_related("portfolio", "benchmark_asset")
            .order_by("-created_at", "id")
        )
        return Response(
            OptimizationRunSerializer(cast(Any, queryset), many=True).data,
            status=status.HTTP_200_OK,
        )

    serializer = OptimizationRunCreateRequestSerializer(data=request.data)
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
        run = create_optimization_run(
            user=user,
            command=serializer.to_command(),
            provider_name=configuration.default_provider,
            resolver=get_asset_resolver(),
            provider=provider,
            executor=execute_market_bar_query,
        )
    except Portfolio.DoesNotExist:
        return Response(
            {"code": "NOT_FOUND", "detail": "Portfolio not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except OptimizationApplicationError as exc:
        return Response(
            {"code": "VALIDATION_ERROR", "errors": {"non_field_errors": [str(exc)]}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        OptimizationRunSerializer(run).data,
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    operation_id="optimization_run_detail",
    description="Return one optimization run owned by the authenticated user.",
    responses={
        status.HTTP_200_OK: OptimizationRunSerializer,
        status.HTTP_404_NOT_FOUND: OpenApiResponse(
            response=OptimizationApiErrorSerializer,
            description="Run does not exist in the authenticated user's scope.",
        ),
    },
    tags=["optimization"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def optimization_run_detail_view(request: Request, run_id: UUID) -> Response:
    """Return one owner-scoped optimization run without cross-user disclosure."""
    user = cast(User, request.user)
    run = (
        OptimizationRun.objects.filter(user=user)
        .select_related("portfolio", "benchmark_asset")
        .filter(id=run_id)
        .first()
    )
    if run is None:
        return Response(
            {"code": "NOT_FOUND", "detail": "Optimization run not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(OptimizationRunSerializer(run).data, status=status.HTTP_200_OK)
