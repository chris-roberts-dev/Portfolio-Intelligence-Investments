"""Deterministic local-demo and Playwright settings.

This module is intentionally isolated from normal development settings. It uses
SQLite plus the committed CSV market-data adapter so the v0.1 demo and browser
suite never depend on external provider credentials or network availability.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = "portfolio-intelligence-demo-only-not-a-secret"
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get(
            "PORTFOLIO_DEMO_DB",
            str(BASE_DIR / ".portfolio-intelligence-demo.sqlite3"),  # noqa: F405
        ),
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

MARKET_DATA_DEFAULT_PROVIDER = "csv"
MARKET_DATA_ALLOWED_PROVIDERS = ("csv",)

# Keeps committed sample bars current and reproducible regardless of wall-clock
# time when the local demo or Playwright suite is executed.
PORTFOLIO_FIXED_CURRENT_TIME = datetime(2026, 9, 16, 16, 0, tzinfo=UTC)
