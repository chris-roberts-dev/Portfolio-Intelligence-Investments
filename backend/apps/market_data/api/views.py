"""Thin DRF views for market-data query endpoints."""

from __future__ import annotations

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

from apps.market_data.api.dependencies import (
    get_asset_catalog_writer,
    get_asset_discovery_provider,
    get_asset_resolver,
)
from apps.market_data.api.policies import (
    MarketBarQueryThrottle,
    MarketDataProviderAuthorizationError,
    authorize_market_data_provider_request,
)
from apps.market_data.api.serializers import (
    MarketBarApiErrorSerializer,
    MarketBarBatchResultSerializer,
    MarketBarQuerySerializer,
    MarketBarValidationErrorSerializer,
)
from apps.market_data.providers.configuration import (
    ProviderConfigurationError,
    load_market_data_provider_configuration,
    resolve_market_data_provider,
)
from apps.market_data.providers.registry import ProviderRegistryError
from apps.market_data.providers.safety import sanitize_provider_message
from apps.market_data.services.asset_discovery import (
    execute_market_bar_query_with_discovery,
)
from apps.market_data.services.market_bar_query import (
    MarketBarOrchestrationError,
)


@extend_schema(
    operation_id="market_data_bars_query",
    description="Resolve symbols and return bounded canonical daily market bars.",
    request=MarketBarQuerySerializer,
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            response=MarketBarBatchResultSerializer,
            description=(
                "The provider completed the request. Inspect each ordered "
                "symbol result for SUCCEEDED, NOT_FOUND, NO_DATA, or FAILED."
            ),
        ),
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(
            response=MarketBarValidationErrorSerializer,
            description="Request or provider-selection validation failed.",
        ),
        status.HTTP_403_FORBIDDEN: OpenApiResponse(
            response=MarketBarApiErrorSerializer,
            description=(
                "The authenticated user is not authorized to request the "
                "selected non-default provider."
            ),
        ),
        status.HTTP_429_TOO_MANY_REQUESTS: OpenApiResponse(
            description="The market-bar query throttle was exceeded.",
        ),
        status.HTTP_503_SERVICE_UNAVAILABLE: OpenApiResponse(
            response=MarketBarApiErrorSerializer,
            description=("The configured provider was unavailable or could not be attempted."),
        ),
    },
    tags=["market-data"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([MarketBarQueryThrottle])
def market_bar_query_view(request: Request) -> Response:
    """Validate transport input and delegate market-bar application workflows."""
    request_serializer = MarketBarQuerySerializer(data=request.data)

    if not request_serializer.is_valid():
        return Response(
            {
                "code": "VALIDATION_ERROR",
                "errors": request_serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    query = request_serializer.normalized_query

    try:
        configuration = load_market_data_provider_configuration()
    except ProviderConfigurationError as exc:
        return _service_unavailable_response(
            exc.code.value,
            str(exc),
        )

    try:
        authorize_market_data_provider_request(
            requested_provider=query.provider,
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
            query.provider,
            configuration=configuration,
        )
    except ProviderConfigurationError as exc:
        if query.provider is not None:
            return Response(
                {
                    "code": exc.code.value,
                    "errors": {
                        "provider": [sanitize_provider_message(str(exc))],
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
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

    discovery_provider = get_asset_discovery_provider(
        provider.name,
    )

    try:
        result = execute_market_bar_query_with_discovery(
            query,
            resolver=get_asset_resolver(),
            provider=provider,
            discovery_provider=discovery_provider,
            catalog_writer=(get_asset_catalog_writer() if discovery_provider is not None else None),
        )
    except MarketBarOrchestrationError as exc:
        return Response(
            {
                "code": exc.code.value,
                "errors": {
                    "non_field_errors": [str(exc)],
                },
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    response_serializer = MarketBarBatchResultSerializer(result)

    return Response(
        response_serializer.data,
        status=status.HTTP_200_OK,
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
