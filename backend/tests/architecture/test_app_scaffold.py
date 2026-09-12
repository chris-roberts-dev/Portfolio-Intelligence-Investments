"""Architecture tests for the Phase 1 Django domain-app scaffold."""

from importlib import import_module

from django.apps import AppConfig, apps
from django.conf import settings

EXPECTED_APP_CONFIGS = (
    ("apps.accounts.apps", "AccountsConfig", "apps.accounts", "accounts"),
    ("apps.assets.apps", "AssetsConfig", "apps.assets", "assets"),
    ("apps.market_data.apps", "MarketDataConfig", "apps.market_data", "market_data"),
    ("apps.portfolios.apps", "PortfoliosConfig", "apps.portfolios", "portfolios"),
    ("apps.analytics.apps", "AnalyticsConfig", "apps.analytics", "analytics"),
    (
        "apps.optimization.apps",
        "OptimizationConfig",
        "apps.optimization",
        "optimization",
    ),
    ("apps.backtesting.apps", "BacktestingConfig", "apps.backtesting", "backtesting"),
)

EXPECTED_PLATFORM_APPS = tuple(
    f"{module_name}.{class_name}"
    for module_name, class_name, _app_name, _label in EXPECTED_APP_CONFIGS
)


def test_domain_app_scaffolds_define_explicit_app_configs() -> None:
    """Every Phase 1 project app should expose an explicit AppConfig."""
    for module_name, class_name, expected_name, _label in EXPECTED_APP_CONFIGS:
        module = import_module(module_name)
        config_class = getattr(module, class_name)

        assert issubclass(config_class, AppConfig)
        assert config_class.name == expected_name


def test_platform_apps_are_registered_and_loaded() -> None:
    """Django should load every project app through the explicit platform registry."""
    assert tuple(settings.PLATFORM_APPS) == EXPECTED_PLATFORM_APPS

    loaded_platform_apps = {
        app_config.name: app_config
        for app_config in apps.get_app_configs()
        if app_config.name.startswith("apps.")
    }

    assert set(loaded_platform_apps) == {
        app_name for _module_name, _class_name, app_name, _label in EXPECTED_APP_CONFIGS
    }

    for _module_name, _class_name, app_name, expected_label in EXPECTED_APP_CONFIGS:
        assert loaded_platform_apps[app_name].label == expected_label
