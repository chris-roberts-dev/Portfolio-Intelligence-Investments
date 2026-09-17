from pathlib import Path


def test_rebalancing_kernel_has_no_framework_or_provider_imports() -> None:
    root = Path(__file__).resolve().parents[2] / "portfolio_engine" / "rebalancing"
    forbidden = ("django", "rest_framework", "yfinance", "apps.", "celery")
    for path in root.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path} imports forbidden boundary {token!r}"
