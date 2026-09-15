from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from apps.market_data.api.views import market_bar_query_view
from config.health import health_view

urlpatterns = [
    path(
        "api/v1/health/",
        health_view,
        name="api-v1-health",
    ),
    path(
        "api/v1/market-data/bars/query/",
        market_bar_query_view,
        name="api-v1-market-data-bars-query",
    ),
    path(
        "api/v1/",
        include("apps.portfolios.api.urls"),
    ),
    path(
        "api/v1/schema/",
        SpectacularAPIView.as_view(),
        name="api-v1-schema",
    ),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(
            url_name="api-v1-schema",
        ),
        name="api-v1-docs",
    ),
]
