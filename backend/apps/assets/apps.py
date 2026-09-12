"""Django application configuration for assets."""

from django.apps import AppConfig


class AssetsConfig(AppConfig):
    """Application configuration for asset persistence and resolution."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.assets"
    verbose_name = "Assets"
