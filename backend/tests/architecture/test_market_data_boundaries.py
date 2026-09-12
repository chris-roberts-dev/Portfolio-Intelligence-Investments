"""Architecture tests for the Phase 2 market-data contract boundary."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]

CONTRACT_PATHS = (
    BACKEND_ROOT / "portfolio_engine" / "contracts" / "market_data.py",
    BACKEND_ROOT / "apps" / "market_data" / "providers" / "base.py",
)

FORBIDDEN_IMPORT_ROOTS = {
    "alpaca",
    "celery",
    "django",
    "httpx",
    "redis",
    "requests",
    "rest_framework",
    "yfinance",
}


def imported_root_names(path: Path) -> set[str]:
    """Return top-level imported module names from a Python source file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", maxsplit=1)[0])

    return roots


def test_market_data_contracts_are_framework_and_provider_independent() -> None:
    """Contracts must not pull framework, HTTP, or provider SDK dependencies."""
    violations: dict[str, list[str]] = {}

    for path in CONTRACT_PATHS:
        forbidden = sorted(imported_root_names(path) & FORBIDDEN_IMPORT_ROOTS)
        if forbidden:
            violations[str(path.relative_to(BACKEND_ROOT))] = forbidden

    assert violations == {}
