"""Explicit immutable response contracts for Django session authentication."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from apps.accounts.models import User


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Safe current-user fields exposed to the browser session."""

    id: UUID
    email: str
    first_name: str
    last_name: str


@dataclass(frozen=True, slots=True)
class AuthSessionResult:
    """Current browser-session authentication state."""

    authenticated: bool
    user: AuthenticatedUser | None


def session_result_for_user(user: User | None) -> AuthSessionResult:
    """Return the safe transport contract for one authenticated user or anonymous state."""
    if user is None:
        return AuthSessionResult(
            authenticated=False,
            user=None,
        )

    return AuthSessionResult(
        authenticated=True,
        user=AuthenticatedUser(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
        ),
    )
