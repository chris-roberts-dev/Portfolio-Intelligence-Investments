"""Django application configuration for rebalancing."""

from django.apps import AppConfig


class RebalancingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.rebalancing"
    verbose_name = "Rebalancing"
