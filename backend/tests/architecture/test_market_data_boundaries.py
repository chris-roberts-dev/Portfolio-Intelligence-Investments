"""Architecture tests for the Phase 2 market-data contract boundary."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]

PURE_MARKET_DATA_PATHS = (
    BACKEND_ROOT / "portfolio_engine" / "config.py",
    BACKEND_ROOT / "portfolio_engine" / "contracts" / "market_data.py",
    BACKEND_ROOT / "portfolio_engine" / "contracts" / "market_data_validation.py",
    BACKEND_ROOT / "portfolio_engine" / "contracts" / "market_data_quality.py",
    BACKEND_ROOT / "portfolio_engine" / "contracts" / "provider_execution.py",
    BACKEND_ROOT / "apps" / "market_data" / "contracts.py",
    BACKEND_ROOT / "apps" / "market_data" / "providers" / "base.py",
    BACKEND_ROOT / "apps" / "market_data" / "providers" / "discovery_base.py",
    BACKEND_ROOT / "apps" / "market_data" / "providers" / "registry.py",
    BACKEND_ROOT / "apps" / "market_data" / "providers" / "mock.py",
    BACKEND_ROOT / "apps" / "market_data" / "providers" / "csv.py",
    BACKEND_ROOT / "apps" / "market_data" / "services" / "asset_resolution.py",
    BACKEND_ROOT / "apps" / "market_data" / "services" / "asset_discovery.py",
    BACKEND_ROOT / "apps" / "market_data" / "services" / "market_bar_query.py",
)

YFINANCE_ADAPTER_PATHS = (
    BACKEND_ROOT / "apps" / "market_data" / "providers" / "yfinance.py",
    BACKEND_ROOT / "apps" / "market_data" / "providers" / "yfinance_discovery.py",
)

FORBIDDEN_PURE_IMPORT_ROOTS = {
    "alpaca",
    "celery",
    "django",
    "httpx",
    "redis",
    "requests",
    "rest_framework",
    "socket",
    "urllib",
    "yfinance",
}


def imported_root_names(path: Path) -> set[str]:
    """Return top-level statically imported module names from a Python file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", maxsplit=1)[0])

    return roots


def dynamically_imported_modules(path: Path) -> set[str]:
    """Return literal modules loaded with importlib.import_module()."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if not isinstance(node.func, ast.Attribute):
            continue

        if node.func.attr != "import_module" or not node.args:
            continue

        module_argument = node.args[0]

        if isinstance(module_argument, ast.Constant) and isinstance(
            module_argument.value,
            str,
        ):
            modules.add(module_argument.value.split(".", maxsplit=1)[0])

    return modules


def test_pure_market_data_boundaries_avoid_forbidden_dependencies() -> None:
    """Pure contracts and application boundaries must stay provider independent."""
    violations: dict[str, list[str]] = {}

    for path in PURE_MARKET_DATA_PATHS:
        forbidden = sorted(imported_root_names(path) & FORBIDDEN_PURE_IMPORT_ROOTS)

        if forbidden:
            violations[str(path.relative_to(BACKEND_ROOT))] = forbidden

    assert violations == {}


def test_yfinance_sdk_loading_is_confined_to_yfinance_adapters() -> None:
    """Only dedicated yfinance adapters may load the yfinance provider package."""
    import_sites: list[str] = []

    for root in (
        BACKEND_ROOT / "apps",
        BACKEND_ROOT / "portfolio_engine",
    ):
        for path in sorted(root.rglob("*.py")):
            imported = imported_root_names(path)
            imported.update(dynamically_imported_modules(path))

            if "yfinance" in imported:
                import_sites.append(str(path.relative_to(BACKEND_ROOT)))

    expected_sites = sorted(str(path.relative_to(BACKEND_ROOT)) for path in YFINANCE_ADAPTER_PATHS)

    assert import_sites == expected_sites
