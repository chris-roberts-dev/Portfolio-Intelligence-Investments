"""Django application configuration for analytics."""

from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    """Application configuration for analytical API orchestration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.analytics"
    verbose_name = "Analytics"
