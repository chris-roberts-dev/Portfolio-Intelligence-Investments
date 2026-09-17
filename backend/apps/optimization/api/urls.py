"""Versioned URL routes for persisted optimization runs."""

from django.urls import path

from apps.optimization.api.views import (
    optimization_run_detail_view,
    optimization_run_list_view,
)

urlpatterns = [
    path(
        "optimization-runs/",
        optimization_run_list_view,
        name="api-v1-optimization-run-list",
    ),
    path(
        "optimization-runs/<uuid:run_id>/",
        optimization_run_detail_view,
        name="api-v1-optimization-run-detail",
    ),
]
