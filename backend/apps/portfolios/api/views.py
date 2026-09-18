"""Thin DRF views for authenticated owned-portfolio reads and mutations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, cast
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import Min
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
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
from apps.assets.models import Asset, AssetType
from apps.market_data.api.policies import (
    MarketBarQueryThrottle,
    MarketDataProviderAuthorizationError,
    authorize_market_data_provider_request,
)
from apps.market_data.contracts import MarketBarQueryError
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.providers.configuration import (
    ProviderConfigurationError,
    load_market_data_provider_configuration,
    resolve_market_data_provider,
)
from apps.market_data.providers.registry import ProviderRegistryError
from apps.market_data.providers.safety import sanitize_provider_message
from apps.portfolios.api.contracts import (
    PortfolioAnalysisQuerySerializer,
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
from apps.portfolios.api.management_serializers import (
    PortfolioBenchmarkRequestSerializer,
    PortfolioCreateRequestSerializer,
    PortfolioRenameRequestSerializer,
)
from apps.portfolios.api.serializers import (
    CurrentPortfolioHoldingsSerializer,
    PortfolioAnalyticsResultSerializer,
    PortfolioSummarySerializer,
)
from apps.portfolios.models import Portfolio
from apps.portfolios.services.analytics import (
    PortfolioAnalyticsError,
    analyze_owned_portfolio,
)
from apps.portfolios.services.current_valuation import (
    CurrentValuationError,
    TradingSessionCalendar,
    value_owned_portfolio,
)
from apps.portfolios.services.daily_performance import DailyPerformanceError
from apps.portfolios.services.portfolio_lifecycle import (
    PortfolioDeletionError,
    delete_empty_owned_portfolio,
)


@dataclass(frozen=True, slots=True)
class _ProviderContext:
    name: str
    provider: MarketDataProvider


@extend_schema_view(
    get=extend_schema(
        operation_id="portfolio_list",
        description="List portfolios owned by the authenticated user.",
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                response=PortfolioSummarySerializer(many=True),
                description="Owned portfolio summaries.",
            ),
        },
        tags=["portfolios"],
    ),
    post=extend_schema(
        operation_id="portfolio_create",
        description=(
            "Create one USD portfolio owned by the authenticated user. Ownership is "
            "derived exclusively from the authenticated session."
        ),
        request=PortfolioCreateRequestSerializer,
        responses={
            status.HTTP_201_CREATED: OpenApiResponse(
                response=PortfolioSummarySerializer,
                description="Created owned portfolio.",
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=PortfolioValidationErrorSerializer,
                description="Portfolio name validation failed.",
            ),
        },
        tags=["portfolios"],
    ),
)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def portfolio_list_view(request: Request) -> Response:
    """List owned portfolios or create one owned by the authenticated principal."""
    user = cast(User, request.user)

    if request.method == "POST":
        serializer = PortfolioCreateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_response(serializer.errors)

        portfolio = Portfolio(
            user=user,
            name=serializer.name_value,
            base_currency="USD",
        )
        try:
            portfolio.full_clean()
            portfolio.save()
        except ValidationError as exc:
            return _validation_response(
                getattr(exc, "message_dict", {"non_field_errors": exc.messages})
            )

        return Response(
            PortfolioSummarySerializer(portfolio).data,
            status=status.HTTP_201_CREATED,
        )

    portfolios = (
        Portfolio.objects.owned_by(user)
        .select_related("benchmark_asset")
        .annotate(ledger_inception_at=Min("transactions__occurred_at"))
    )
    return Response(
        PortfolioSummarySerializer(
            cast(Any, portfolios),
            many=True,
        ).data,
        status=status.HTTP_200_OK,
    )


@extend_schema_view(
    get=extend_schema(
        operation_id="portfolio_detail",
        description="Return one portfolio owned by the authenticated user.",
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                response=PortfolioSummarySerializer,
                description="Owned portfolio summary.",
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(
                response=PortfolioApiErrorSerializer,
                description=("The portfolio does not exist in the authenticated user's scope."),
            ),
        },
        tags=["portfolios"],
    ),
    patch=extend_schema(
        operation_id="portfolio_rename",
        description="Rename one portfolio owned by the authenticated user.",
        request=PortfolioRenameRequestSerializer,
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                response=PortfolioSummarySerializer,
                description="Renamed owned portfolio.",
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                response=PortfolioValidationErrorSerializer,
                description="Portfolio name validation failed.",
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(
                response=PortfolioApiErrorSerializer,
                description=("The portfolio does not exist in the authenticated user's scope."),
            ),
        },
        tags=["portfolios"],
    ),
    delete=extend_schema(
        operation_id="portfolio_delete",
        description=(
            "Permanently delete one owned portfolio only when it has no persisted "
            "transaction or analytical history."
        ),
        request=None,
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(
                description="Empty owned portfolio permanently deleted.",
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(
                response=PortfolioApiErrorSerializer,
                description=("The portfolio does not exist in the authenticated user's scope."),
            ),
            status.HTTP_409_CONFLICT: OpenApiResponse(
                response=PortfolioApiErrorSerializer,
                description=(
                    "Permanent deletion is blocked because retained transaction or "
                    "analytical history exists."
                ),
            ),
        },
        tags=["portfolios"],
    ),
)
@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def portfolio_detail_view(
    request: Request,
    portfolio_id: UUID,
) -> Response:
    """Read, rename, or safely delete one owner-scoped portfolio."""
    user = cast(User, request.user)

    if request.method == "DELETE":
        try:
            delete_empty_owned_portfolio(
                user=user,
                portfolio_id=portfolio_id,
            )
        except Portfolio.DoesNotExist:
            return _portfolio_not_found_response()
        except PortfolioDeletionError as exc:
            return Response(
                {
                    "code": exc.code.value,
                    "detail": str(exc),
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    portfolio = _owned_portfolio(user, portfolio_id)

    if portfolio is None:
        return _portfolio_not_found_response()

    if request.method == "PATCH":
        serializer = PortfolioRenameRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_response(serializer.errors)

        portfolio.name = serializer.name_value
        try:
            portfolio.full_clean()
            portfolio.save(update_fields=("name", "updated_at"))
        except ValidationError as exc:
            return _validation_response(
                getattr(exc, "message_dict", {"non_field_errors": exc.messages})
            )

    return Response(
        PortfolioSummarySerializer(portfolio).data,
        status=status.HTTP_200_OK,
    )


@extend_schema(
    operation_id="portfolio_benchmark_update",
    description=(
        "Select or clear the benchmark for one authenticated-user-owned portfolio "
        "using an active canonical USD stock/ETF asset identity."
    ),
    request=PortfolioBenchmarkRequestSerializer,
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            response=PortfolioSummarySerializer,
            description="Owned portfolio with updated benchmark selection.",
        ),
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(
            response=PortfolioValidationErrorSerializer,
            description="Benchmark asset identity is invalid or unsupported.",
        ),
        status.HTTP_404_NOT_FOUND: OpenApiResponse(
            response=PortfolioApiErrorSerializer,
            description=("The portfolio does not exist in the authenticated user's scope."),
        ),
    },
    tags=["portfolios"],
)
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def portfolio_benchmark_view(
    request: Request,
    portfolio_id: UUID,
) -> Response:
    """Select or clear one owner-scoped portfolio benchmark."""
    user = cast(User, request.user)
    portfolio = _owned_portfolio(user, portfolio_id)

    if portfolio is None:
        return _portfolio_not_found_response()

    serializer = PortfolioBenchmarkRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return _validation_response(serializer.errors)

    benchmark_asset_id = serializer.benchmark_asset_id_value
    benchmark_asset = None

    if benchmark_asset_id is not None:
        benchmark_asset = Asset.objects.filter(
            id=benchmark_asset_id,
            is_active=True,
            currency="USD",
            asset_type__in=(AssetType.STOCK, AssetType.ETF),
        ).first()

        if benchmark_asset is None:
            return _validation_response(
                {
                    "benchmark_asset_id": [
                        "Benchmark asset must reference an active canonical USD stock or ETF."
                    ]
                }
            )

    portfolio.benchmark_asset = benchmark_asset
    portfolio.save(update_fields=("benchmark_asset", "updated_at"))

    return Response(
        PortfolioSummarySerializer(portfolio).data,
        status=status.HTTP_200_OK,
    )


@extend_schema(
    operation_id="portfolio_current_holdings",
    description=(
        "Return ledger-derived current holdings, raw-close valuation, allocation, "
        "warnings, and provenance for an owned portfolio."
    ),
    parameters=[PortfolioProviderQuerySerializer],
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            response=CurrentPortfolioHoldingsSerializer,
            description="Current holdings and valuation result.",
        ),
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(
            response=PortfolioValidationErrorSerializer,
            description="Query or provider-selection validation failed.",
        ),
        status.HTTP_403_FORBIDDEN: OpenApiResponse(
            response=PortfolioApiErrorSerializer,
            description="The selected non-default provider is not authorized.",
        ),
        status.HTTP_404_NOT_FOUND: OpenApiResponse(
            response=PortfolioApiErrorSerializer,
            description="The portfolio does not exist in the authenticated user's scope.",
        ),
        status.HTTP_429_TOO_MANY_REQUESTS: OpenApiResponse(
            description="The provider-backed read throttle was exceeded.",
        ),
        status.HTTP_503_SERVICE_UNAVAILABLE: OpenApiResponse(
            response=PortfolioApiErrorSerializer,
            description="A required provider or valuation dependency is unavailable.",
        ),
    },
    tags=["portfolios"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([MarketBarQueryThrottle])
def portfolio_holdings_view(
    request: Request,
    portfolio_id: UUID,
) -> Response:
    """Delegate current owned-portfolio holdings and valuation orchestration."""
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
        result = value_owned_portfolio(
            user=user,
            portfolio_id=portfolio_id,
            as_of=get_current_time(),
            provider_name=provider_context.name,
            resolver=get_asset_resolver(),
            provider=provider_context.provider,
            trading_calendar=get_trading_session_calendar(),
        )
    except Portfolio.DoesNotExist:
        return _portfolio_not_found_response()
    except TradingSessionCalendarUnavailable as exc:
        return _service_unavailable_response(exc.code, str(exc))
    except MarketBarQueryError as exc:
        return _field_validation_response(
            code=exc.code.value,
            field=exc.field,
            message=str(exc),
        )
    except CurrentValuationError as exc:
        return _service_unavailable_response(
            "PORTFOLIO_VALUATION_FAILED",
            str(exc),
        )

    return Response(
        CurrentPortfolioHoldingsSerializer(result).data,
        status=status.HTTP_200_OK,
    )


@extend_schema(
    operation_id="portfolio_analytics",
    description=(
        "Return owned-portfolio performance/risk analytics for an inclusive-start, "
        "exclusive-end trading-session period."
    ),
    parameters=[PortfolioAnalysisQuerySerializer],
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            response=PortfolioAnalyticsResultSerializer,
            description="Owned-portfolio analytical result and provenance.",
        ),
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(
            response=PortfolioValidationErrorSerializer,
            description="Query or provider-selection validation failed.",
        ),
        status.HTTP_403_FORBIDDEN: OpenApiResponse(
            response=PortfolioApiErrorSerializer,
            description="The selected non-default provider is not authorized.",
        ),
        status.HTTP_404_NOT_FOUND: OpenApiResponse(
            response=PortfolioApiErrorSerializer,
            description="The portfolio does not exist in the authenticated user's scope.",
        ),
        status.HTTP_429_TOO_MANY_REQUESTS: OpenApiResponse(
            description="The provider-backed read throttle was exceeded.",
        ),
        status.HTTP_503_SERVICE_UNAVAILABLE: OpenApiResponse(
            response=PortfolioApiErrorSerializer,
            description="A required provider or analytics dependency is unavailable.",
        ),
    },
    tags=["analytics"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([MarketBarQueryThrottle])
def portfolio_analytics_view(
    request: Request,
    portfolio_id: UUID,
) -> Response:
    """Delegate owner-scoped portfolio analytics orchestration."""
    user = cast(User, request.user)

    if _owned_portfolio(user, portfolio_id) is None:
        return _portfolio_not_found_response()

    query_serializer = PortfolioAnalysisQuerySerializer(
        data=request.query_params,
    )

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
            code="INSUFFICIENT_ANALYTICS_PERIOD",
            field="end",
            message="The requested period must contain at least two trading sessions.",
        )

    try:
        result = analyze_owned_portfolio(
            user=user,
            portfolio_id=portfolio_id,
            valuation_times=valuation_times,
            provider_name=provider_context.name,
            resolver=get_asset_resolver(),
            provider=provider_context.provider,
            trading_calendar=trading_calendar,
            risk_free_rate_annual=query_serializer.risk_free_rate_annual_value,
            minimum_acceptable_return_annual=(
                query_serializer.minimum_acceptable_return_annual_value
            ),
            rolling_window_size=query_serializer.rolling_window_value,
        )
    except Portfolio.DoesNotExist:
        return _portfolio_not_found_response()
    except TradingSessionCalendarUnavailable as exc:
        return _service_unavailable_response(exc.code, str(exc))
    except MarketBarQueryError as exc:
        return _field_validation_response(
            code=exc.code.value,
            field=exc.field,
            message=str(exc),
        )
    except (
        CurrentValuationError,
        DailyPerformanceError,
        PortfolioAnalyticsError,
    ) as exc:
        return _service_unavailable_response(
            "PORTFOLIO_ANALYTICS_FAILED",
            str(exc),
        )

    return Response(
        PortfolioAnalyticsResultSerializer(result).data,
        status=status.HTTP_200_OK,
    )


def _owned_portfolio(
    user: User,
    portfolio_id: UUID,
) -> Portfolio | None:
    return (
        Portfolio.objects.owned_by(user)
        .select_related("benchmark_asset")
        .annotate(ledger_inception_at=Min("transactions__occurred_at"))
        .filter(id=portfolio_id)
        .first()
    )


def _provider_context_for_request(
    request: Request,
    *,
    requested_provider: str | None,
) -> _ProviderContext | Response:
    try:
        configuration = load_market_data_provider_configuration()
    except ProviderConfigurationError as exc:
        return _service_unavailable_response(
            exc.code.value,
            str(exc),
        )

    try:
        authorize_market_data_provider_request(
            requested_provider=requested_provider,
            default_provider=configuration.default_provider,
            is_authenticated=bool(request.user.is_authenticated),
            is_staff=bool(getattr(request.user, "is_staff", False)),
        )
    except MarketDataProviderAuthorizationError as exc:
        return Response(
            {
                "code": exc.code,
                "detail": str(exc),
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        provider = resolve_market_data_provider(
            requested_provider,
            configuration=configuration,
        )
    except ProviderConfigurationError as exc:
        if requested_provider is not None:
            return _field_validation_response(
                code=exc.code.value,
                field="provider",
                message=sanitize_provider_message(str(exc)),
            )

        return _service_unavailable_response(
            exc.code.value,
            str(exc),
        )
    except ProviderRegistryError as exc:
        return _service_unavailable_response(
            exc.code.value,
            str(exc),
        )
    except RuntimeError as exc:
        return _service_unavailable_response(
            "PROVIDER_INITIALIZATION_FAILED",
            str(exc),
        )

    return _ProviderContext(
        name=provider.name,
        provider=provider,
    )


def _analytics_valuation_times(
    *,
    start: date,
    end: date,
    trading_calendar: TradingSessionCalendar,
) -> tuple[datetime, ...]:
    calendar_days = (end - start).days
    if calendar_days <= 0:
        raise ValueError("analytics end must be after start")

    final_candidate = end - timedelta(days=1)
    sessions = trading_calendar.sessions_through(
        final_candidate,
        count=calendar_days + 1,
    )

    if tuple(sorted(set(sessions))) != sessions:
        raise ValueError("trading sessions must be unique and strictly ascending")

    if sessions and sessions[-1] > final_candidate:
        raise ValueError("trading sessions must not extend beyond the requested period")

    selected_sessions = tuple(session for session in sessions if start <= session < end)

    return tuple(
        datetime.combine(
            session,
            time.max,
            tzinfo=UTC,
        )
        for session in selected_sessions
    )


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


def _field_validation_response(
    *,
    code: str,
    field: str,
    message: str,
) -> Response:
    return Response(
        {
            "code": code,
            "errors": {
                field: [message],
            },
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def _service_unavailable_response(
    code: str,
    detail: str,
) -> Response:
    return Response(
        {
            "code": code,
            "detail": sanitize_provider_message(detail),
        },
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )
