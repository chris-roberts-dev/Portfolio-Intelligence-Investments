"""Versioned URL routes for persisted backtest runs."""

from django.urls import path

from apps.backtesting.api.views import backtest_run_detail_view, backtest_run_list_view

urlpatterns = [
    path("backtest-runs/", backtest_run_list_view, name="api-v1-backtest-run-list"),
    path(
        "backtest-runs/<uuid:run_id>/",
        backtest_run_detail_view,
        name="api-v1-backtest-run-detail",
    ),
]
