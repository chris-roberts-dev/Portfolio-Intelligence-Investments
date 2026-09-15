"""Thin authenticated endpoint for the canonical dashboard snapshot."""

from __future__ import annotations

from typing import cast
from uuid import UUID

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.models import User
from apps.market_data.api.policies import MarketBarQueryThrottle
from apps.portfolios.api.contracts import (
    PortfolioApiErrorSerializer,
    PortfolioValidationErrorSerializer,
)
from apps.portfolios.api.dashboard_snapshot_serializers import (
    DashboardSnapshotQuerySerializer,
    DashboardSnapshotResultSerializer,
)
from apps.portfolios.api.dependencies import (
    TradingSessionCalendarUnavailable,
    get_asset_resolver,
    get_current_time,
    get_trading_session_calendar,
)
from apps.portfolios.api.views import (
    _analytics_valuation_times,
    _field_validation_response,
    _owned_portfolio,
    _portfolio_not_found_response,
    _provider_context_for_request,
    _service_unavailable_response,
    _validation_response,
)
from apps.portfolios.models import Portfolio
from apps.portfolios.services.dashboard_snapshot import (
    DashboardSnapshotError,
    build_owned_portfolio_dashboard_snapshot,
)


@extend_schema(
    operation_id="portfolio_dashboard_snapshot",
    description=(
        "Return one coherent owner-scoped dashboard snapshot using a shared "
        "provider, calculation cutoff, trading-session range, and request-local "
        "market-data query cache. Individual dashboard modules may be unavailable "
        "without failing the complete response."
    ),
    parameters=[DashboardSnapshotQuerySerializer],
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            response=DashboardSnapshotResultSerializer,
            description="Canonical dashboard snapshot and module states.",
        ),
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(
            response=PortfolioValidationErrorSerializer,
            description="Range, assumptions, or provider validation failed.",
        ),
        status.HTTP_403_FORBIDDEN: OpenApiResponse(
            response=PortfolioApiErrorSerializer,
            description=("The selected non-default provider is not authorized."),
        ),
        status.HTTP_404_NOT_FOUND: OpenApiResponse(
            response=PortfolioApiErrorSerializer,
            description=("The portfolio does not exist in the authenticated user's scope."),
        ),
        status.HTTP_429_TOO_MANY_REQUESTS: OpenApiResponse(
            description="The provider-backed read throttle was exceeded.",
        ),
        status.HTTP_503_SERVICE_UNAVAILABLE: OpenApiResponse(
            response=PortfolioApiErrorSerializer,
            description=("A shared dashboard dependency or snapshot context is unavailable."),
        ),
    },
    tags=["portfolios"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([MarketBarQueryThrottle])
def portfolio_dashboard_snapshot_view(
    request: Request,
    portfolio_id: UUID,
) -> Response:
    """Return one canonical owner-scoped dashboard snapshot."""
    user = cast(User, request.user)

    if _owned_portfolio(user, portfolio_id) is None:
        return _portfolio_not_found_response()

    query_serializer = DashboardSnapshotQuerySerializer(data=request.query_params)

    if not query_serializer.is_valid():
        return _validation_response(query_serializer.errors)

    provider_context = _provider_context_for_request(
        request,
        requested_provider=query_serializer.requested_provider,
    )

    if isinstance(provider_context, Response):
        return provider_context

    calculated_at = get_current_time()

    try:
        trading_calendar = get_trading_session_calendar()
        requested_valuation_times = _analytics_valuation_times(
            start=query_serializer.start_date,
            end=query_serializer.end_date,
            trading_calendar=trading_calendar,
        )
    except TradingSessionCalendarUnavailable as exc:
        return _service_unavailable_response(exc.code, str(exc))
    except ValueError as exc:
        return _service_unavailable_response(
            "TRADING_CALENDAR_INVALID",
            str(exc),
        )

    valuation_times = tuple(
        valuation_time
        for valuation_time in requested_valuation_times
        if valuation_time <= calculated_at
    )

    if len(valuation_times) < 2:
        return _field_validation_response(
            code="INSUFFICIENT_DASHBOARD_PERIOD",
            field="end",
            message=(
                "The requested period must contain at least two completed "
                "trading-session valuation points before the snapshot cutoff."
            ),
        )

    try:
        result = build_owned_portfolio_dashboard_snapshot(
            user=user,
            portfolio_id=portfolio_id,
            valuation_times=valuation_times,
            requested_start=query_serializer.start_date,
            requested_end=query_serializer.end_date,
            provider_name=provider_context.name,
            resolver=get_asset_resolver(),
            provider=provider_context.provider,
            trading_calendar=trading_calendar,
            calculated_at=calculated_at,
            movers_limit=query_serializer.movers_limit_value,
            risk_free_rate_annual=(query_serializer.risk_free_rate_annual_value),
            minimum_acceptable_return_annual=(
                query_serializer.minimum_acceptable_return_annual_value
            ),
        )
    except Portfolio.DoesNotExist:
        return _portfolio_not_found_response()
    except DashboardSnapshotError as exc:
        return _service_unavailable_response(
            "PORTFOLIO_DASHBOARD_SNAPSHOT_FAILED",
            str(exc),
        )

    return Response(
        DashboardSnapshotResultSerializer(result).data,
        status=status.HTTP_200_OK,
    )
