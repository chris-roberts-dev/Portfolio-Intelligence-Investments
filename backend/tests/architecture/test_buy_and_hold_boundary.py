import ast
from pathlib import Path


def test_strategy_package_has_no_framework_provider_or_application_imports() -> None:
    root = Path(__file__).resolve().parents[2] / "portfolio_engine" / "strategies"
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


def test_backtesting_kernel_still_does_not_depend_on_django_backtesting_app() -> None:
    root = Path(__file__).resolve().parents[2] / "portfolio_engine" / "backtesting"
    for path in root.glob("*.py"):
        assert "apps.backtesting" not in path.read_text(encoding="utf-8")
