"""Thin DRF endpoint for dashboard-ready owned-portfolio holdings."""

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
from apps.portfolios.api.holdings_dashboard_serializers import (
    DashboardHoldingsResultSerializer,
)
from apps.portfolios.api.performance_serializers import (
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
from apps.portfolios.services.current_valuation import (
    CurrentValuationError,
)
from apps.portfolios.services.dashboard_holdings import (
    DashboardHoldingsError,
    build_owned_portfolio_dashboard_holdings,
)


@extend_schema(
    operation_id="portfolio_dashboard_holdings",
    description=(
        "Return display-ready current holdings with exact-date "
        "selected-period adjusted-close movement and "
        "non-interpolated sparkline points."
    ),
    parameters=[PortfolioPerformanceQuerySerializer],
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            response=DashboardHoldingsResultSerializer,
            description="Dashboard-ready owned-portfolio holdings.",
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
            description=("A required provider, calendar, valuation, or history dependency failed."),
        ),
    },
    tags=["portfolios"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([MarketBarQueryThrottle])
def portfolio_dashboard_holdings_view(
    request: Request,
    portfolio_id: UUID,
) -> Response:
    """Return one owner-scoped dashboard holdings result."""
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
        return _service_unavailable_response(
            exc.code,
            str(exc),
        )
    except ValueError as exc:
        return _service_unavailable_response(
            "TRADING_CALENDAR_INVALID",
            str(exc),
        )

    if len(valuation_times) < 2:
        return _field_validation_response(
            code="INSUFFICIENT_HOLDINGS_PERIOD",
            field="end",
            message=("The requested period must contain at least two trading sessions."),
        )

    calculated_at = get_current_time()

    try:
        result = build_owned_portfolio_dashboard_holdings(
            user=user,
            portfolio_id=portfolio_id,
            observation_dates=tuple(valuation_time.date() for valuation_time in valuation_times),
            requested_start=query_serializer.start_date,
            requested_end=query_serializer.end_date,
            provider_name=provider_context.name,
            resolver=get_asset_resolver(),
            provider=provider_context.provider,
            trading_calendar=trading_calendar,
            calculated_at=calculated_at,
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
        CurrentValuationError,
        DashboardHoldingsError,
    ) as exc:
        return _service_unavailable_response(
            "PORTFOLIO_HOLDINGS_FAILED",
            str(exc),
        )

    return Response(
        DashboardHoldingsResultSerializer(result).data,
        status=status.HTTP_200_OK,
    )
