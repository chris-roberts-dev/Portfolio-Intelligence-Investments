"""Versioned Django session authentication routes."""

from django.urls import path

from apps.accounts.api.views import login_view, logout_view, session_view

urlpatterns = [
    path(
        "session/",
        session_view,
        name="api-v1-auth-session",
    ),
    path(
        "login/",
        login_view,
        name="api-v1-auth-login",
    ),
    path(
        "logout/",
        logout_view,
        name="api-v1-auth-logout",
    ),
]
