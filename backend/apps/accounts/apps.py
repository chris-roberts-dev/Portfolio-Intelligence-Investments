"""Django application configuration for user accounts."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Application configuration for Portfolio Intelligence accounts."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Accounts"

    def ready(self) -> None:
        """Register account-specific OpenAPI extensions."""
        from apps.accounts import schema  # noqa: F401
