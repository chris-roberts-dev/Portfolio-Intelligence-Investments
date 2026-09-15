"""Architecture checks for Phase 4 market-sensitive portfolio dependencies."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]

DEPENDENCY_PATHS = (
    BACKEND_ROOT / "apps" / "assets" / "resolution.py",
    BACKEND_ROOT / "apps" / "portfolios" / "services" / "trading_calendar.py",
)

FORBIDDEN_IMPORT_ROOTS = {
    "alpaca",
    "httpx",
    "requests",
    "socket",
    "yfinance",
}


def imported_root_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", maxsplit=1)[0])

    return roots


def test_portfolio_market_dependencies_do_not_import_provider_sdks_or_network_clients() -> None:
    violations = {
        str(path.relative_to(BACKEND_ROOT)): sorted(
            imported_root_names(path) & FORBIDDEN_IMPORT_ROOTS
        )
        for path in DEPENDENCY_PATHS
        if imported_root_names(path) & FORBIDDEN_IMPORT_ROOTS
    }

    assert violations == {}
