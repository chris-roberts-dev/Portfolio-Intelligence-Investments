"""Integration coverage for CSRF-safe Django browser sessions."""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.portfolios.models import Portfolio

PASSWORD = "correct-horse-battery-staple"


def _csrf_client() -> tuple[APIClient, str]:
    client = APIClient(enforce_csrf_checks=True)
    response = client.get(reverse("api-v1-auth-session"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "authenticated": False,
        "user": None,
    }
    assert "csrftoken" in response.cookies

    return client, response.cookies["csrftoken"].value


@pytest.mark.django_db
def test_session_bootstrap_is_anonymous_and_issues_csrf_cookie() -> None:
    client = APIClient(enforce_csrf_checks=True)

    response = client.get(reverse("api-v1-auth-session"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "authenticated": False,
        "user": None,
    }
    assert response.cookies["csrftoken"].value


@pytest.mark.django_db
def test_login_requires_csrf_and_returns_only_safe_user_fields() -> None:
    user = User.objects.create_user(
        email="Owner@Example.com",
        password=PASSWORD,
        first_name="Portfolio",
        last_name="Owner",
    )
    client, _csrf_token = _csrf_client()

    missing_csrf = client.post(
        reverse("api-v1-auth-login"),
        {
            "email": "owner@example.com",
            "password": PASSWORD,
        },
        format="json",
    )

    assert missing_csrf.status_code == status.HTTP_403_FORBIDDEN
    assert missing_csrf.data == {
        "code": "CSRF_FAILED",
        "detail": "CSRF validation failed.",
    }

    csrf_token = client.cookies["csrftoken"].value
    response = client.post(
        reverse("api-v1-auth-login"),
        {
            "email": "OWNER@example.com",
            "password": PASSWORD,
        },
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "authenticated": True,
        "user": {
            "id": str(user.id),
            "email": "owner@example.com",
            "first_name": "Portfolio",
            "last_name": "Owner",
        },
    }
    assert set(response.data["user"]) == {
        "id",
        "email",
        "first_name",
        "last_name",
    }
    assert "sessionid" in client.cookies


@pytest.mark.django_db
def test_invalid_credentials_are_generic_and_do_not_create_session() -> None:
    User.objects.create_user(
        email="owner@example.com",
        password=PASSWORD,
    )
    client, csrf_token = _csrf_client()

    response = client.post(
        reverse("api-v1-auth-login"),
        {
            "email": "owner@example.com",
            "password": "incorrect-password",
        },
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.data == {
        "code": "INVALID_CREDENTIALS",
        "detail": "Invalid email or password.",
    }
    assert "sessionid" not in client.cookies


@pytest.mark.django_db
def test_authenticated_session_persists_and_portfolios_remain_owner_scoped() -> None:
    owner = User.objects.create_user(
        email="owner@example.com",
        password=PASSWORD,
    )
    other = User.objects.create_user(
        email="other@example.com",
        password=PASSWORD,
    )
    owner_portfolio = Portfolio.objects.create(
        user=owner,
        name="Owner Portfolio",
    )
    Portfolio.objects.create(
        user=other,
        name="Other Portfolio",
    )
    client, csrf_token = _csrf_client()

    login_response = client.post(
        reverse("api-v1-auth-login"),
        {
            "email": owner.email,
            "password": PASSWORD,
        },
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert login_response.status_code == status.HTTP_200_OK

    session_response = client.get(reverse("api-v1-auth-session"))
    assert session_response.status_code == status.HTTP_200_OK
    assert session_response.data["authenticated"] is True
    assert session_response.data["user"]["id"] == str(owner.id)

    portfolio_response = client.get(reverse("api-v1-portfolio-list"))
    assert portfolio_response.status_code == status.HTTP_200_OK
    assert [item["id"] for item in portfolio_response.data] == [str(owner_portfolio.id)]


@pytest.mark.django_db
def test_logout_requires_csrf_and_destroys_authenticated_session() -> None:
    user = User.objects.create_user(
        email="owner@example.com",
        password=PASSWORD,
    )
    client, csrf_token = _csrf_client()
    login_response = client.post(
        reverse("api-v1-auth-login"),
        {
            "email": user.email,
            "password": PASSWORD,
        },
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert login_response.status_code == status.HTTP_200_OK

    missing_csrf = client.post(
        reverse("api-v1-auth-logout"),
        {},
        format="json",
    )
    assert missing_csrf.status_code == status.HTTP_403_FORBIDDEN
    assert missing_csrf.data["code"] == "CSRF_FAILED"

    rotated_csrf_token = client.cookies["csrftoken"].value
    response = client.post(
        reverse("api-v1-auth-logout"),
        {},
        format="json",
        HTTP_X_CSRFTOKEN=rotated_csrf_token,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "authenticated": False,
        "user": None,
    }

    session_response = client.get(reverse("api-v1-auth-session"))
    assert session_response.status_code == status.HTTP_200_OK
    assert session_response.data["authenticated"] is False
    assert session_response.data["user"] is None
