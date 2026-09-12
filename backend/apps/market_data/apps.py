"""Django application configuration for market data."""

from django.apps import AppConfig


class MarketDataConfig(AppConfig):
    """Application configuration for market-data orchestration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.market_data"
    verbose_name = "Market Data"
