"""Thin authenticated endpoint for the P0 allocation visualization."""

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
from apps.portfolios.api.allocation_serializers import (
    DashboardAllocationResultSerializer,
)
from apps.portfolios.api.contracts import (
    PortfolioApiErrorSerializer,
    PortfolioProviderQuerySerializer,
    PortfolioValidationErrorSerializer,
)
from apps.portfolios.api.dependencies import (
    TradingSessionCalendarUnavailable,
    get_asset_resolver,
    get_current_time,
    get_trading_session_calendar,
)
from apps.portfolios.api.views import (
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
from apps.portfolios.services.dashboard_allocation import (
    DashboardAllocationError,
    build_owned_portfolio_dashboard_allocation,
)


@extend_schema(
    operation_id="portfolio_dashboard_allocation",
    description=(
        "Return the P0 current portfolio asset-class allocation using "
        "authoritative valuation/allocation weights, explicit cash, "
        "deterministic ordering, and disclosed grouping rules."
    ),
    parameters=[PortfolioProviderQuerySerializer],
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            response=DashboardAllocationResultSerializer,
            description="Dashboard-ready current allocation.",
        ),
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(
            response=PortfolioValidationErrorSerializer,
            description="Provider-selection validation failed.",
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
            description=(
                "A required provider, calendar, valuation, or allocation dependency failed."
            ),
        ),
    },
    tags=["portfolios"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([MarketBarQueryThrottle])
def portfolio_dashboard_allocation_view(
    request: Request,
    portfolio_id: UUID,
) -> Response:
    """Return one owner-scoped current allocation result."""
    user = cast(User, request.user)

    if _owned_portfolio(user, portfolio_id) is None:
        return _portfolio_not_found_response()

    query_serializer = PortfolioProviderQuerySerializer(data=request.query_params)

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
        result = build_owned_portfolio_dashboard_allocation(
            user=user,
            portfolio_id=portfolio_id,
            provider_name=provider_context.name,
            resolver=get_asset_resolver(),
            provider=provider_context.provider,
            trading_calendar=trading_calendar,
            calculated_at=get_current_time(),
        )
    except TradingSessionCalendarUnavailable as exc:
        return _service_unavailable_response(
            exc.code,
            str(exc),
        )
    except Portfolio.DoesNotExist:
        return _portfolio_not_found_response()
    except MarketBarQueryError as exc:
        return Response(
            {
                "code": exc.code.value,
                "errors": {
                    exc.field: [str(exc)],
                },
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except (
        CurrentValuationError,
        DashboardAllocationError,
    ) as exc:
        return _service_unavailable_response(
            "PORTFOLIO_ALLOCATION_FAILED",
            str(exc),
        )

    return Response(
        DashboardAllocationResultSerializer(result).data,
        status=status.HTTP_200_OK,
    )
