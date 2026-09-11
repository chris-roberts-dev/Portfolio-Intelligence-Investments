"""Regression tests for the generated OpenAPI contract."""

import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


def test_openapi_schema_exposes_health_contract_and_docs() -> None:
    """The generated schema should contain the explicit health API contract."""
    client = APIClient()

    schema_response = client.get(
        reverse("api-v1-schema"),
        HTTP_ACCEPT="application/vnd.oai.openapi+json",
    )

    assert schema_response.status_code == status.HTTP_200_OK

    schema = json.loads(schema_response.content)
    health_path = schema["paths"]["/api/v1/health/"]
    health_operation = health_path["get"]

    assert health_operation["operationId"] == "health_check"
    assert "post" not in health_path
    assert "200" in health_operation["responses"]

    docs_response = client.get(reverse("api-v1-docs"))

    assert docs_response.status_code == status.HTTP_200_OK
