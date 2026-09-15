"""Versioned owned-portfolio read API routes."""

from django.urls import path

from apps.portfolios.api.holdings_dashboard_views import (
    portfolio_dashboard_holdings_view,
)
from apps.portfolios.api.performance_views import (
    portfolio_performance_view,
)
from apps.portfolios.api.views import (
    portfolio_analytics_view,
    portfolio_detail_view,
    portfolio_holdings_view,
    portfolio_list_view,
)

urlpatterns = [
    path(
        "portfolios/",
        portfolio_list_view,
        name="api-v1-portfolio-list",
    ),
    path(
        "portfolios/<uuid:portfolio_id>/",
        portfolio_detail_view,
        name="api-v1-portfolio-detail",
    ),
    path(
        "portfolios/<uuid:portfolio_id>/holdings/",
        portfolio_holdings_view,
        name="api-v1-portfolio-holdings",
    ),
    path(
        "portfolios/<uuid:portfolio_id>/holdings/dashboard/",
        portfolio_dashboard_holdings_view,
        name="api-v1-portfolio-dashboard-holdings",
    ),
    path(
        "portfolios/<uuid:portfolio_id>/performance/",
        portfolio_performance_view,
        name="api-v1-portfolio-performance",
    ),
    path(
        "analytics/portfolios/<uuid:portfolio_id>/",
        portfolio_analytics_view,
        name="api-v1-portfolio-analytics",
    ),
]
