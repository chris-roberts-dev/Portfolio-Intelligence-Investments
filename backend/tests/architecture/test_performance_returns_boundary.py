"""Focused architecture coverage for performance return calculations."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
RETURNS_PATH = BACKEND_ROOT / "portfolio_engine" / "performance" / "returns.py"

FORBIDDEN_IMPORT_ROOTS = {
    "alpaca",
    "apps",
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


def test_returns_kernel_has_no_application_framework_or_provider_imports() -> None:
    assert imported_root_names(RETURNS_PATH) & FORBIDDEN_IMPORT_ROOTS == set()
