import json

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_openapi_exposes_historical_rebalancing_comparison_resource() -> None:
    response = APIClient().get(
        reverse("api-v1-schema"),
        HTTP_ACCEPT="application/vnd.oai.openapi+json",
    )
    assert response.status_code == status.HTTP_200_OK
    schema = json.loads(response.content)
    collection = schema["paths"]["/api/v1/historical-rebalance-comparisons/"]
    assert collection["post"]["operationId"] == "historical_rebalance_comparison_create"
    assert collection["get"]["operationId"] == "historical_rebalance_comparison_list"
