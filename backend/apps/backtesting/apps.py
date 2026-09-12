"""Django application configuration for backtesting."""

from django.apps import AppConfig


class BacktestingConfig(AppConfig):
    """Application configuration for backtesting workflows."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.backtesting"
    verbose_name = "Backtesting"
