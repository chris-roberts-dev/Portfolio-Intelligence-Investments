"""Authenticated owner-scoped Phase 5 target and rebalancing endpoints."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from drf_spectacular.utils import extend_schema, extend_schema_view
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
from apps.portfolios.api.dependencies import (
    TradingSessionCalendarUnavailable,
    get_asset_resolver,
    get_current_time,
    get_trading_session_calendar,
)
from apps.portfolios.models import Portfolio
from apps.rebalancing.api.serializers import (
    HistoricalRebalanceComparisonCreateRequestSerializer,
    HistoricalRebalanceComparisonSerializer,
    RebalanceSimulationCreateRequestSerializer,
    RebalanceSimulationSerializer,
    RebalancingApiErrorSerializer,
    RebalancingValidationErrorSerializer,
    TargetAllocationCreateRequestSerializer,
    TargetAllocationSerializer,
)
from apps.rebalancing.models import (
    HistoricalRebalanceComparison,
    RebalanceSimulation,
    TargetAllocation,
)
from apps.rebalancing.services import (
    RebalancingApplicationError,
    create_historical_rebalance_comparison,
    create_rebalance_simulation,
    create_target_allocation,
)


@extend_schema_view(
    get=extend_schema(
        operation_id="target_allocation_list",
        responses={200: TargetAllocationSerializer(many=True)},
        tags=["rebalancing"],
    ),
    post=extend_schema(
        operation_id="target_allocation_create",
        request=TargetAllocationCreateRequestSerializer,
        responses={
            201: TargetAllocationSerializer,
            400: RebalancingValidationErrorSerializer,
            404: RebalancingApiErrorSerializer,
        },
        tags=["rebalancing"],
    ),
)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def target_allocation_list_view(request: Request) -> Response:
    user = cast(User, request.user)
    if request.method == "GET":
        queryset = TargetAllocation.objects.filter(user=user).prefetch_related("weights__asset")
        return Response(TargetAllocationSerializer(cast(Any, queryset), many=True).data)
    serializer = TargetAllocationCreateRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"code": "VALIDATION_ERROR", "errors": serializer.errors}, status=400)
    try:
        target = create_target_allocation(user=user, command=serializer.to_command())
    except Portfolio.DoesNotExist:
        return Response({"code": "NOT_FOUND", "detail": "Portfolio not found."}, status=404)
    except RebalancingApplicationError as exc:
        return Response(
            {"code": "VALIDATION_ERROR", "errors": {"non_field_errors": [str(exc)]}}, status=400
        )
    return Response(TargetAllocationSerializer(target).data, status=201)


@extend_schema(
    operation_id="target_allocation_detail",
    responses={200: TargetAllocationSerializer, 404: RebalancingApiErrorSerializer},
    tags=["rebalancing"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def target_allocation_detail_view(request: Request, target_id: UUID) -> Response:
    user = cast(User, request.user)
    target = (
        TargetAllocation.objects.filter(user=user, id=target_id)
        .prefetch_related("weights__asset")
        .first()
    )
    if target is None:
        return Response({"code": "NOT_FOUND", "detail": "Target allocation not found."}, status=404)
    return Response(TargetAllocationSerializer(target).data)


@extend_schema_view(
    get=extend_schema(
        operation_id="rebalance_simulation_list",
        responses={200: RebalanceSimulationSerializer(many=True)},
        tags=["rebalancing"],
    ),
    post=extend_schema(
        operation_id="rebalance_simulation_create",
        request=RebalanceSimulationCreateRequestSerializer,
        responses={
            201: RebalanceSimulationSerializer,
            400: RebalancingValidationErrorSerializer,
            404: RebalancingApiErrorSerializer,
            503: RebalancingApiErrorSerializer,
        },
        tags=["rebalancing"],
    ),
)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def rebalance_simulation_list_view(request: Request) -> Response:
    user = cast(User, request.user)
    if request.method == "GET":
        queryset = RebalanceSimulation.objects.filter(user=user).select_related(
            "portfolio", "target_allocation"
        )
        return Response(RebalanceSimulationSerializer(cast(Any, queryset), many=True).data)
    serializer = RebalanceSimulationCreateRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"code": "VALIDATION_ERROR", "errors": serializer.errors}, status=400)
    try:
        configuration = load_market_data_provider_configuration()
        provider = resolve_market_data_provider(configuration=configuration)
        simulation = create_rebalance_simulation(
            user=user,
            command=serializer.to_command(),
            as_of=get_current_time(),
            provider_name=configuration.default_provider,
            resolver=get_asset_resolver(),
            provider=provider,
            trading_calendar=get_trading_session_calendar(),
        )
    except Portfolio.DoesNotExist:
        return Response({"code": "NOT_FOUND", "detail": "Portfolio not found."}, status=404)
    except (
        ProviderConfigurationError,
        ProviderRegistryError,
        TradingSessionCalendarUnavailable,
    ) as exc:
        return Response({"code": "DEPENDENCY_UNAVAILABLE", "detail": str(exc)}, status=503)
    except RebalancingApplicationError as exc:
        return Response(
            {"code": "VALIDATION_ERROR", "errors": {"non_field_errors": [str(exc)]}}, status=400
        )
    return Response(RebalanceSimulationSerializer(simulation).data, status=201)


@extend_schema(
    operation_id="rebalance_simulation_detail",
    responses={200: RebalanceSimulationSerializer, 404: RebalancingApiErrorSerializer},
    tags=["rebalancing"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def rebalance_simulation_detail_view(request: Request, simulation_id: UUID) -> Response:
    user = cast(User, request.user)
    simulation = RebalanceSimulation.objects.filter(user=user, id=simulation_id).first()
    if simulation is None:
        return Response(
            {"code": "NOT_FOUND", "detail": "Rebalance simulation not found."}, status=404
        )
    return Response(RebalanceSimulationSerializer(simulation).data)


@extend_schema_view(
    get=extend_schema(
        operation_id="historical_rebalance_comparison_list",
        responses={200: HistoricalRebalanceComparisonSerializer(many=True)},
        tags=["rebalancing"],
    ),
    post=extend_schema(
        operation_id="historical_rebalance_comparison_create",
        request=HistoricalRebalanceComparisonCreateRequestSerializer,
        responses={
            201: HistoricalRebalanceComparisonSerializer,
            400: RebalancingValidationErrorSerializer,
            404: RebalancingApiErrorSerializer,
            503: RebalancingApiErrorSerializer,
        },
        tags=["rebalancing"],
    ),
)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def historical_rebalance_comparison_list_view(request: Request) -> Response:
    user = cast(User, request.user)
    if request.method == "GET":
        queryset = HistoricalRebalanceComparison.objects.filter(user=user).select_related(
            "portfolio", "target_allocation"
        )
        return Response(
            HistoricalRebalanceComparisonSerializer(cast(Any, queryset), many=True).data
        )

    serializer = HistoricalRebalanceComparisonCreateRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"code": "VALIDATION_ERROR", "errors": serializer.errors}, status=400)

    try:
        configuration = load_market_data_provider_configuration()
        provider = resolve_market_data_provider(configuration=configuration)
        comparison = create_historical_rebalance_comparison(
            user=user,
            command=serializer.to_command(),
            provider_name=configuration.default_provider,
            resolver=get_asset_resolver(),
            provider=provider,
            trading_calendar=get_trading_session_calendar(),
        )
    except Portfolio.DoesNotExist:
        return Response({"code": "NOT_FOUND", "detail": "Portfolio not found."}, status=404)
    except (
        ProviderConfigurationError,
        ProviderRegistryError,
        TradingSessionCalendarUnavailable,
    ) as exc:
        return Response({"code": "DEPENDENCY_UNAVAILABLE", "detail": str(exc)}, status=503)
    except RebalancingApplicationError as exc:
        if exc.code == "TARGET_ALLOCATION_NOT_FOUND":
            return Response({"code": "NOT_FOUND", "detail": str(exc)}, status=404)
        return Response(
            {"code": exc.code, "errors": {"non_field_errors": [str(exc)]}},
            status=400,
        )

    return Response(HistoricalRebalanceComparisonSerializer(comparison).data, status=201)


@extend_schema(
    operation_id="historical_rebalance_comparison_detail",
    responses={200: HistoricalRebalanceComparisonSerializer, 404: RebalancingApiErrorSerializer},
    tags=["rebalancing"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def historical_rebalance_comparison_detail_view(request: Request, comparison_id: UUID) -> Response:
    user = cast(User, request.user)
    comparison = HistoricalRebalanceComparison.objects.filter(user=user, id=comparison_id).first()
    if comparison is None:
        return Response(
            {"code": "NOT_FOUND", "detail": "Historical rebalance comparison not found."},
            status=404,
        )
    return Response(HistoricalRebalanceComparisonSerializer(comparison).data)
