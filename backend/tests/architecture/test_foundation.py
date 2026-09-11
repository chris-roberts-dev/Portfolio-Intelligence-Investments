"""Foundation architecture invariants from development guide Sections 4.2 and 5.2."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = BACKEND_ROOT / "portfolio_engine"
FORBIDDEN_ENGINE_IMPORTS = {
    "alpaca",
    "apps",
    "celery",
    "config",
    "django",
    "httpx",
    "redis",
    "requests",
    "rest_framework",
    "yfinance",
}


def imported_root_names(path: Path) -> set[str]:
    """Return top-level imported module names from a Python source file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", maxsplit=1)[0])

    return roots


def test_custom_user_model_is_selected_before_first_migration() -> None:
    """The project must not fall back to Django's default integer-PK user model."""
    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.db.models import UUIDField

    user_model = get_user_model()

    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert user_model._meta.label == "accounts.User"
    assert isinstance(user_model._meta.pk, UUIDField)


def test_custom_user_model_uses_email_as_authentication_identity() -> None:
    """Authentication must use normalized email instead of Django's username field."""
    from django.contrib.auth import get_user_model
    from django.core.exceptions import FieldDoesNotExist

    user_model = get_user_model()

    assert user_model.USERNAME_FIELD == "email"
    assert user_model.REQUIRED_FIELDS == []
    assert user_model._meta.get_field("email").unique is True
    assert user_model.objects.normalize_email(" Example.User@EXAMPLE.COM ") == (
        "example.user@example.com"
    )

    try:
        user_model._meta.get_field("username")
    except FieldDoesNotExist:
        pass
    else:
        raise AssertionError("The custom user model must not define a username field")


def test_portfolio_engine_has_no_framework_or_infrastructure_imports() -> None:
    """Keep application frameworks and provider clients outside the quantitative engine."""
    violations: dict[str, list[str]] = {}

    for path in sorted(ENGINE_ROOT.rglob("*.py")):
        forbidden = sorted(imported_root_names(path) & FORBIDDEN_ENGINE_IMPORTS)
        if forbidden:
            violations[str(path.relative_to(BACKEND_ROOT))] = forbidden

    assert violations == {}
