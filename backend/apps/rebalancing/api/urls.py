"""Versioned Phase 5 rebalancing routes."""

from django.urls import path

from apps.rebalancing.api.views import (
    historical_rebalance_comparison_detail_view,
    historical_rebalance_comparison_list_view,
    rebalance_simulation_detail_view,
    rebalance_simulation_list_view,
    target_allocation_detail_view,
    target_allocation_list_view,
)

urlpatterns = [
    path("target-allocations/", target_allocation_list_view, name="api-v1-target-allocation-list"),
    path(
        "target-allocations/<uuid:target_id>/",
        target_allocation_detail_view,
        name="api-v1-target-allocation-detail",
    ),
    path(
        "rebalance-simulations/",
        rebalance_simulation_list_view,
        name="api-v1-rebalance-simulation-list",
    ),
    path(
        "rebalance-simulations/<uuid:simulation_id>/",
        rebalance_simulation_detail_view,
        name="api-v1-rebalance-simulation-detail",
    ),
    path(
        "historical-rebalance-comparisons/",
        historical_rebalance_comparison_list_view,
        name="api-v1-historical-rebalance-comparison-list",
    ),
    path(
        "historical-rebalance-comparisons/<uuid:comparison_id>/",
        historical_rebalance_comparison_detail_view,
        name="api-v1-historical-rebalance-comparison-detail",
    ),
]
