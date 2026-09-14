"""Architecture tests for the framework-independent quantitative kernel."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PERFORMANCE_ROOT = BACKEND_ROOT / "portfolio_engine" / "performance"

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
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", maxsplit=1)[0])

    return roots


def test_performance_kernel_has_no_framework_or_provider_imports() -> None:
    violations: dict[str, list[str]] = {}

    for path in sorted(PERFORMANCE_ROOT.rglob("*.py")):
        forbidden = sorted(imported_root_names(path) & FORBIDDEN_IMPORT_ROOTS)

        if forbidden:
            violations[str(path.relative_to(BACKEND_ROOT))] = forbidden

    assert violations == {}
