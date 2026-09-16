"""Local-development Django settings."""

from __future__ import annotations

import os

from .base import *  # noqa: F403

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() in {"1", "true", "yes", "on"}
ALLOWED_HOSTS = ALLOWED_HOSTS or ["localhost", "127.0.0.1"]  # noqa: F405

MARKET_DATA_DEFAULT_PROVIDER = (
    os.environ.get(
        "MARKET_DATA_DEFAULT_PROVIDER",
        "yfinance",
    )
    .strip()
    .lower()
)

MARKET_DATA_ALLOWED_PROVIDERS = tuple(
    provider.strip().lower()
    for provider in os.environ.get(
        "MARKET_DATA_ALLOWED_PROVIDERS",
        "yfinance,mock,csv",
    ).split(",")
    if provider.strip()
)
