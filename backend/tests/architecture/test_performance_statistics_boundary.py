"""Architecture coverage for volatility and Sharpe calculations."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
STATISTICS_PATH = BACKEND_ROOT / "portfolio_engine" / "performance" / "statistics.py"

FORBIDDEN_IMPORT_ROOTS = {
    "alpaca",
    "apps",
    "celery",
    "datetime",
    "django",
    "httpx",
    "os",
    "redis",
    "requests",
    "rest_framework",
    "socket",
    "time",
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


def test_statistics_kernel_has_no_application_framework_or_provider_imports() -> None:
    assert imported_root_names(STATISTICS_PATH) & FORBIDDEN_IMPORT_ROOTS == set()
