"""Market-data API throttling and provider-authorization policies."""

from __future__ import annotations

import os
import re

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rest_framework.throttling import UserRateThrottle

DEFAULT_MARKET_DATA_BAR_QUERY_THROTTLE_RATE = "60/min"
MARKET_DATA_BAR_QUERY_THROTTLE_RATE_SETTING = "MARKET_DATA_BAR_QUERY_THROTTLE_RATE"

_THROTTLE_RATE_PATTERN = re.compile(
    r"^[1-9]\d*/(?:s|sec|second|m|min|minute|h|hour|d|day)s?$",
    re.IGNORECASE,
)


class MarketDataProviderAuthorizationError(PermissionError):
    """Raised when a principal may not request a non-default provider."""

    code = "NON_DEFAULT_PROVIDER_FORBIDDEN"


def get_market_bar_query_throttle_rate() -> str:
    """Return the validated settings/environment-driven endpoint throttle rate."""
    configured_rate = getattr(
        settings,
        MARKET_DATA_BAR_QUERY_THROTTLE_RATE_SETTING,
        None,
    )

    if configured_rate is None:
        configured_rate = os.environ.get(
            MARKET_DATA_BAR_QUERY_THROTTLE_RATE_SETTING,
            DEFAULT_MARKET_DATA_BAR_QUERY_THROTTLE_RATE,
        )

    if not isinstance(configured_rate, str):
        raise ImproperlyConfigured("MARKET_DATA_BAR_QUERY_THROTTLE_RATE must be a string.")

    normalized_rate = configured_rate.strip()

    if not _THROTTLE_RATE_PATTERN.fullmatch(normalized_rate):
        raise ImproperlyConfigured(
            "MARKET_DATA_BAR_QUERY_THROTTLE_RATE must use a positive DRF rate such as '60/min'."
        )

    return normalized_rate


class MarketBarQueryThrottle(UserRateThrottle):
    """Per-user throttle for the bounded market-bar query endpoint."""

    scope = "market_data_bars_query"

    def get_rate(self) -> str:
        return get_market_bar_query_throttle_rate()


def authorize_market_data_provider_request(
    *,
    requested_provider: str | None,
    default_provider: str,
    is_authenticated: bool,
    is_staff: bool,
) -> None:
    """Authorize an explicit provider choice independently of the allowlist."""
    normalized_default = default_provider.strip().lower()

    if not normalized_default:
        raise ValueError("default_provider must not be blank")

    normalized_requested = (
        requested_provider.strip().lower() if requested_provider is not None else None
    )

    if normalized_requested is None or normalized_requested == normalized_default:
        return

    if is_authenticated and is_staff:
        return

    raise MarketDataProviderAuthorizationError(
        "Explicit use of a non-default market-data provider requires staff authorization."
    )
