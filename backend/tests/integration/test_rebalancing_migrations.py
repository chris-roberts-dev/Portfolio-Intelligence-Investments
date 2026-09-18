from __future__ import annotations

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_historical_rebalance_comparison_is_represented_in_migration_state() -> None:
    executor = MigrationExecutor(connection)
    project_state = executor.loader.project_state()
    assert ("rebalancing", "historicalrebalancecomparison") in project_state.models
    assert executor.loader.graph.leaf_nodes("rebalancing")
