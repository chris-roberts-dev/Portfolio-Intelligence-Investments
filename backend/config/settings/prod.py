from __future__ import annotations

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403


def require_environment(name: str) -> str:
    """Return a required environment variable or fail application startup."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} must be set in production")
    return value


DEBUG = False
SECRET_KEY = require_environment("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = [
    host.strip() for host in require_environment("DJANGO_ALLOWED_HOSTS").split(",") if host.strip()
]

if SECRET_KEY == DEVELOPMENT_SECRET_KEY:  # noqa: F405
    raise ImproperlyConfigured("The development secret key cannot be used in production")
