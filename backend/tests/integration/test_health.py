"""Integration tests for the versioned framework health endpoint."""

from rest_framework import status
from rest_framework.test import APIClient


def test_health_endpoint_returns_ok() -> None:
    """The versioned health route should be reachable without authentication."""
    response = APIClient().get("/api/v1/health/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_health_endpoint_rejects_writes() -> None:
    """The health endpoint is read-only."""
    response = APIClient().post("/api/v1/health/", {}, format="json")

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
