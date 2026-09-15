"""OpenAPI regression coverage for Django session authentication."""

import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


def test_openapi_exposes_session_login_and_logout_contracts() -> None:
    response = APIClient().get(
        reverse("api-v1-schema"),
        HTTP_ACCEPT="application/vnd.oai.openapi+json",
    )

    assert response.status_code == status.HTTP_200_OK

    schema = json.loads(response.content)
    paths = schema["paths"]

    session = paths["/api/v1/auth/session/"]["get"]
    login = paths["/api/v1/auth/login/"]["post"]
    logout = paths["/api/v1/auth/logout/"]["post"]

    assert session["operationId"] == "auth_session"
    assert login["operationId"] == "auth_login"
    assert logout["operationId"] == "auth_logout"

    assert session["tags"] == ["auth"]
    assert login["tags"] == ["auth"]
    assert logout["tags"] == ["auth"]

    assert set(session["responses"]) == {"200"}
    assert set(login["responses"]) == {
        "200",
        "400",
        "401",
        "403",
    }
    assert set(logout["responses"]) == {
        "200",
        "401",
        "403",
    }

    components = schema["components"]["schemas"]
    assert "AuthenticatedUser" in components
    assert "AuthSessionResult" in components
    assert "LoginRequest" in components
    assert "AuthApiError" in components
    assert "AuthValidationError" in components
