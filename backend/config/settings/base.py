from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

DEVELOPMENT_SECRET_KEY = "development-only-change-me"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", DEVELOPMENT_SECRET_KEY)
DEBUG = False

ALLOWED_HOSTS = [
    host.strip() for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if host.strip()
]

DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
]

PLATFORM_APPS = [
    "apps.accounts.apps.AccountsConfig",
    "apps.assets.apps.AssetsConfig",
    "apps.market_data.apps.MarketDataConfig",
    "apps.portfolios.apps.PortfoliosConfig",
    "apps.analytics.apps.AnalyticsConfig",
    "apps.optimization.apps.OptimizationConfig",
    "apps.rebalancing.apps.RebalancingConfig",
    "apps.backtesting.apps.BacktestingConfig",
]

INSTALLED_APPS = [
    *DJANGO_APPS,
    *PLATFORM_APPS,
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "portfolio_intelligence"),
        "USER": os.environ.get("POSTGRES_USER", "portfolio_intelligence"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 0,
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MARKET_DATA_DEFAULT_PROVIDER = (
    os.environ.get(
        "MARKET_DATA_DEFAULT_PROVIDER",
        "mock",
    )
    .strip()
    .lower()
)

MARKET_DATA_ALLOWED_PROVIDERS = tuple(
    provider.strip().lower()
    for provider in os.environ.get(
        "MARKET_DATA_ALLOWED_PROVIDERS",
        "mock",
    ).split(",")
    if provider.strip()
)

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Portfolio Intelligence API",
    "VERSION": "0.1.0",
    "ENUM_NAME_OVERRIDES": {
        "PerformanceDataQualityEnum": (
            "apps.portfolios.services.dashboard_performance.PerformanceDataQualityState"
        ),
        "HoldingMetricUnavailableReasonEnum": (
            "apps.portfolios.services.dashboard_holdings.HoldingMetricUnavailableReason"
        ),
        "PortfolioSummaryUnavailableReasonEnum": (
            "apps.portfolios.services.dashboard_summary.PortfolioSummaryUnavailableReason"
        ),
        "OptimizationRunMethodEnum": "apps.optimization.models.OptimizationRunMethod",
        "OptimizationRunStatusEnum": "apps.optimization.models.OptimizationRunStatus",
        "RebalanceScheduleEnum": "portfolio_engine.rebalancing.contracts.RebalanceSchedule",
        "BacktestStrategyEnum": "apps.backtesting.models.BacktestStrategyName",
    },
}
