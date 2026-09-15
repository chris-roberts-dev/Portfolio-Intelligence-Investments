"""DRF request and response contracts for Django session authentication."""

from __future__ import annotations

from typing import Any, cast

from rest_framework import serializers

from apps.accounts.api.contracts import AuthenticatedUser, AuthSessionResult


class AuthenticatedUserSerializer(serializers.Serializer[AuthenticatedUser]):
    """Safe current-user fields only."""

    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)


class AuthSessionResultSerializer(serializers.Serializer[AuthSessionResult]):
    """Current browser-session authentication state."""

    authenticated = serializers.BooleanField(read_only=True)
    user = AuthenticatedUserSerializer(
        read_only=True,
        allow_null=True,
    )


class LoginRequestSerializer(serializers.Serializer[object]):
    """Email/password login request."""

    email = serializers.EmailField(
        write_only=True,
        trim_whitespace=True,
    )
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        max_length=128,
    )

    @property
    def email_value(self) -> str:
        return cast(str, self.validated_data["email"])

    @property
    def password_value(self) -> str:
        return cast(str, self.validated_data["password"])


class AuthApiErrorSerializer(serializers.Serializer[object]):
    """Stable authentication/session error response."""

    code = serializers.CharField(read_only=True)
    detail = serializers.CharField(read_only=True)


class AuthValidationErrorSerializer(serializers.Serializer[object]):
    """Stable authentication request validation error response."""

    code = serializers.CharField(read_only=True)
    errors = cast(
        Any,
        serializers.DictField(
            child=serializers.ListField(
                child=serializers.CharField(),
            ),
            read_only=True,
        ),
    )
