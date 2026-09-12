"""Django application configuration for optimization."""

from django.apps import AppConfig


class OptimizationConfig(AppConfig):
    """Application configuration for optimization workflows."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.optimization"
    verbose_name = "Optimization"
