from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager["User"]):
    """Create users whose authentication identity is their normalized email address."""

    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email: str | None) -> str:
        """Normalize email identities for consistent case-insensitive authentication."""
        return super().normalize_email(email).strip().lower()

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        """Create and persist a standard user identified by email."""
        if not email:
            raise ValueError("An email address is required")

        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        """Create and persist a staff superuser identified by email."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, **extra_fields)

    def get_by_natural_key(self, username: str | None) -> User:
        """Resolve authentication identities without email-case sensitivity."""
        return self.get(email__iexact=self.normalize_email(username))

    async def aget_by_natural_key(self, username: str | None) -> User:
        """Resolve authentication identities asynchronously without case sensitivity."""
        return await self.aget(email__iexact=self.normalize_email(username))


class User(AbstractBaseUser, PermissionsMixin):
    """Portfolio Intelligence user authenticated by email with a UUID primary key."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    EMAIL_FIELD: ClassVar[str] = "email"
    USERNAME_FIELD: ClassVar[str] = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    objects: ClassVar[UserManager] = UserManager()

    def clean(self) -> None:
        """Normalize the persisted authentication identity."""
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self) -> str:
        """Return the user's first and last names."""
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self) -> str:
        """Return the user's first name."""
        return self.first_name.strip()
