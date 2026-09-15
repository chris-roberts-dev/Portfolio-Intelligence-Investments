"""Migration-state coverage for the first Phase 4 domain models."""

from __future__ import annotations

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_phase4_domain_models_are_represented_in_migration_state() -> None:
    executor = MigrationExecutor(connection)
    project_state = executor.loader.project_state()

    expected_models = {
        ("assets", "asset"),
        ("assets", "assetprovidersymbol"),
        ("portfolios", "portfolio"),
        ("portfolios", "transaction"),
    }

    assert expected_models <= set(project_state.models)
    assert executor.loader.graph.leaf_nodes("assets")
    assert executor.loader.graph.leaf_nodes("portfolios")
