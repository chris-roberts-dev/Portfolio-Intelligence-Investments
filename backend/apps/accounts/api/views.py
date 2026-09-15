"""CSRF-safe Django session authentication endpoints."""

from __future__ import annotations

from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.api.contracts import session_result_for_user
from apps.accounts.api.serializers import (
    AuthApiErrorSerializer,
    AuthSessionResultSerializer,
    AuthValidationErrorSerializer,
    LoginRequestSerializer,
)
from apps.accounts.models import User


class _CsrfDeferredSessionAuthentication(SessionAuthentication):
    """Authenticate the session while deferring CSRF to the stable API guard."""

    def enforce_csrf(self, request: Request) -> None:
        return


@extend_schema(
    operation_id="auth_session",
    description=(
        "Return the current Django browser-session state and issue the CSRF cookie "
        "required by login/logout POST requests."
    ),
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            response=AuthSessionResultSerializer,
            description="Current authenticated or anonymous session state.",
        ),
    },
    tags=["auth"],
)
@ensure_csrf_cookie
@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def session_view(request: Request) -> Response:
    """Return safe current-user state without requiring an authenticated session."""
    authenticated_user = request.user if isinstance(request.user, User) else None
    result = session_result_for_user(authenticated_user)

    return Response(
        AuthSessionResultSerializer(result).data,
        status=status.HTTP_200_OK,
    )


@extend_schema(
    operation_id="auth_login",
    description=(
        "Authenticate an email/password identity and establish a Django session. "
        "A valid CSRF token from GET /api/v1/auth/session/ is required."
    ),
    request=LoginRequestSerializer,
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            response=AuthSessionResultSerializer,
            description="Authenticated browser-session state.",
        ),
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(
            response=AuthValidationErrorSerializer,
            description="Email/password request validation failed.",
        ),
        status.HTTP_401_UNAUTHORIZED: OpenApiResponse(
            response=AuthApiErrorSerializer,
            description="The supplied email/password pair is invalid.",
        ),
        status.HTTP_403_FORBIDDEN: OpenApiResponse(
            response=AuthApiErrorSerializer,
            description="CSRF validation failed.",
        ),
    },
    tags=["auth"],
)
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login_view(request: Request) -> Response:
    """Create a Django session after CSRF and credential validation."""
    csrf_failure = _csrf_failure_response(request)
    if csrf_failure is not None:
        return csrf_failure

    serializer = LoginRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {
                "code": "VALIDATION_ERROR",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    normalized_email = User.objects.normalize_email(serializer.email_value)
    authenticated = authenticate(
        request=request._request,
        username=normalized_email,
        password=serializer.password_value,
    )

    if not isinstance(authenticated, User):
        return Response(
            {
                "code": "INVALID_CREDENTIALS",
                "detail": "Invalid email or password.",
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    django_login(
        request._request,
        authenticated,
    )
    result = session_result_for_user(authenticated)

    return Response(
        AuthSessionResultSerializer(result).data,
        status=status.HTTP_200_OK,
    )


@extend_schema(
    operation_id="auth_logout",
    description=(
        "Destroy the current Django session. A valid session and CSRF token are required."
    ),
    request=None,
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            response=AuthSessionResultSerializer,
            description="Anonymous browser-session state after logout.",
        ),
        status.HTTP_401_UNAUTHORIZED: OpenApiResponse(
            response=AuthApiErrorSerializer,
            description="No authenticated session is present.",
        ),
        status.HTTP_403_FORBIDDEN: OpenApiResponse(
            response=AuthApiErrorSerializer,
            description="Authentication or CSRF validation failed.",
        ),
    },
    tags=["auth"],
)
@api_view(["POST"])
@authentication_classes([_CsrfDeferredSessionAuthentication])
@permission_classes([IsAuthenticated])
def logout_view(request: Request) -> Response:
    """Destroy the authenticated Django session after explicit CSRF validation."""
    csrf_failure = _csrf_failure_response(request)
    if csrf_failure is not None:
        return csrf_failure

    django_logout(request._request)
    result = session_result_for_user(None)

    return Response(
        AuthSessionResultSerializer(result).data,
        status=status.HTTP_200_OK,
    )


def _csrf_failure_response(request: Request) -> Response | None:
    """Apply SessionAuthentication's CSRF check even before login exists."""
    try:
        SessionAuthentication().enforce_csrf(request)
    except PermissionDenied:
        return Response(
            {
                "code": "CSRF_FAILED",
                "detail": "CSRF validation failed.",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    return None
