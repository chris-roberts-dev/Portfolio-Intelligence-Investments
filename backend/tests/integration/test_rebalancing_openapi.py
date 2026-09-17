import json

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_openapi_exposes_target_and_rebalance_resources() -> None:
    response = APIClient().get(
        reverse("api-v1-schema"),
        HTTP_ACCEPT="application/vnd.oai.openapi+json",
    )
    assert response.status_code == status.HTTP_200_OK
    schema = json.loads(response.content)
    paths = schema["paths"]
    assert paths["/api/v1/target-allocations/"]["post"]["operationId"] == "target_allocation_create"
    assert (
        paths["/api/v1/rebalance-simulations/"]["post"]["operationId"]
        == "rebalance_simulation_create"
    )
