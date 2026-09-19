import ast
from pathlib import Path


def test_backtesting_kernel_has_no_framework_provider_or_application_imports() -> None:
    root = Path(__file__).resolve().parents[2] / "portfolio_engine" / "backtesting"
    forbidden_prefixes = (
        "django",
        "rest_framework",
        "yfinance",
        "apps",
        "celery",
        "requests",
        "httpx",
    )

    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported_modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.append(node.module)

        for module in imported_modules:
            assert not module.startswith(forbidden_prefixes), (
                f"{path} imports forbidden boundary {module!r}"
            )


def test_phase5_rebalancing_does_not_depend_on_phase6_backtesting() -> None:
    path = (
        Path(__file__).resolve().parents[2] / "portfolio_engine" / "rebalancing" / "historical.py"
    )
    text = path.read_text(encoding="utf-8")
    assert "portfolio_engine.backtesting" not in text
    assert "StrategyContext" not in text
