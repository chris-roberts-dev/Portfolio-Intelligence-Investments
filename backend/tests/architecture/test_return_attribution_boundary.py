from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ATTRIBUTION_PATH = BACKEND_ROOT / "portfolio_engine" / "portfolio" / "return_attribution.py"

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


def imported_root_names(
    path: Path,
) -> set[str]:
    tree = ast.parse(
        path.read_text(encoding="utf-8"),
        filename=str(path),
    )
    roots: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(
            node,
            ast.Import,
        ):
            roots.update(
                alias.name.split(
                    ".",
                    maxsplit=1,
                )[0]
                for alias in node.names
            )
        elif (
            isinstance(
                node,
                ast.ImportFrom,
            )
            and node.module
        ):
            roots.add(
                node.module.split(
                    ".",
                    maxsplit=1,
                )[0]
            )

    return roots


def test_return_attribution_remains_framework_independent() -> None:
    assert imported_root_names(ATTRIBUTION_PATH) & FORBIDDEN_IMPORT_ROOTS == set()
