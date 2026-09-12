"""Django application configuration for portfolios."""

from django.apps import AppConfig


class PortfoliosConfig(AppConfig):
    """Application configuration for portfolio persistence and workflows."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.portfolios"
    verbose_name = "Portfolios"
