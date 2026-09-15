"""Architecture coverage for framework-independent concentration calculations."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
CONCENTRATION_PATH = BACKEND_ROOT / "portfolio_engine" / "risk" / "concentration.py"

FORBIDDEN_IMPORT_ROOTS = {
    "alpaca",
    "apps",
    "celery",
    "django",
    "httpx",
    "numpy",
    "os",
    "pandas",
    "redis",
    "requests",
    "rest_framework",
    "socket",
    "yfinance",
}


def imported_root_names(path: Path) -> set[str]:
    tree = ast.parse(
        path.read_text(encoding="utf-8"),
        filename=str(path),
    )
    roots: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", maxsplit=1)[0])

    return roots


def test_concentration_kernel_has_no_framework_or_provider_imports() -> None:
    assert imported_root_names(CONCENTRATION_PATH) & FORBIDDEN_IMPORT_ROOTS == set()
