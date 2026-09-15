"""Thin DRF endpoint for dashboard portfolio performance."""

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
from apps.market_data.contracts import MarketBarQueryError
from apps.portfolios.api.contracts import (
    PortfolioApiErrorSerializer,
    PortfolioValidationErrorSerializer,
)
from apps.portfolios.api.dependencies import (
    TradingSessionCalendarUnavailable,
    get_asset_resolver,
    get_current_time,
    get_trading_session_calendar,
)
from apps.portfolios.api.performance_serializers import (
    DashboardPerformanceResultSerializer,
    PortfolioPerformanceQuerySerializer,
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
from apps.portfolios.services.daily_performance import (
    DailyPerformanceError,
)
from apps.portfolios.services.dashboard_performance import (
    DashboardPerformanceError,
    build_owned_portfolio_dashboard_performance,
)


@extend_schema(
    operation_id="portfolio_performance",
    description=(
        "Return display-ready daily portfolio value/TWR points and an "
        "optional exact-date benchmark series for an "
        "inclusive-start/exclusive-end period."
    ),
    parameters=[PortfolioPerformanceQuerySerializer],
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            response=DashboardPerformanceResultSerializer,
            description=("Display-ready portfolio performance series and provenance."),
        ),
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(
            response=PortfolioValidationErrorSerializer,
            description=("Date-range or provider-selection validation failed."),
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
            description=("The provider-backed read throttle was exceeded."),
        ),
        status.HTTP_503_SERVICE_UNAVAILABLE: OpenApiResponse(
            response=PortfolioApiErrorSerializer,
            description=("A required provider, calendar, or performance dependency failed."),
        ),
    },
    tags=["portfolios"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([MarketBarQueryThrottle])
def portfolio_performance_view(
    request: Request,
    portfolio_id: UUID,
) -> Response:
    """Return one owner-scoped display-ready performance series."""
    user = cast(User, request.user)

    if _owned_portfolio(user, portfolio_id) is None:
        return _portfolio_not_found_response()

    query_serializer = PortfolioPerformanceQuerySerializer(data=request.query_params)

    if not query_serializer.is_valid():
        return _validation_response(query_serializer.errors)

    provider_context = _provider_context_for_request(
        request,
        requested_provider=query_serializer.requested_provider,
    )

    if isinstance(provider_context, Response):
        return provider_context

    try:
        trading_calendar = get_trading_session_calendar()
        valuation_times = _analytics_valuation_times(
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

    if len(valuation_times) < 2:
        return _field_validation_response(
            code="INSUFFICIENT_PERFORMANCE_PERIOD",
            field="end",
            message=("The requested period must contain at least two trading sessions."),
        )

    try:
        result = build_owned_portfolio_dashboard_performance(
            user=user,
            portfolio_id=portfolio_id,
            valuation_times=valuation_times,
            requested_start=query_serializer.start_date,
            requested_end=query_serializer.end_date,
            provider_name=provider_context.name,
            resolver=get_asset_resolver(),
            provider=provider_context.provider,
            trading_calendar=trading_calendar,
            calculated_at=get_current_time(),
        )
    except Portfolio.DoesNotExist:
        return _portfolio_not_found_response()
    except MarketBarQueryError as exc:
        return _field_validation_response(
            code=exc.code.value,
            field=exc.field,
            message=str(exc),
        )
    except (
        DailyPerformanceError,
        DashboardPerformanceError,
    ) as exc:
        return _service_unavailable_response(
            "PORTFOLIO_PERFORMANCE_FAILED",
            str(exc),
        )

    return Response(
        DashboardPerformanceResultSerializer(result).data,
        status=status.HTTP_200_OK,
    )
