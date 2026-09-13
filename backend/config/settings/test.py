"""Deterministic Django settings for automated tests."""

from .base import *  # noqa: F403

SECRET_KEY = "test-only-secret-key"
DEBUG = False
ALLOWED_HOSTS = ["testserver"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

MARKET_DATA_DEFAULT_PROVIDER = "mock"
MARKET_DATA_ALLOWED_PROVIDERS = ("mock",)
