"""Framework-level health endpoint for Portfolio Intelligence."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response


class HealthResponseSerializer(serializers.Serializer):
    """OpenAPI response contract for the framework health endpoint."""

    status = serializers.CharField(read_only=True)


@extend_schema(
    operation_id="health_check",
    responses={status.HTTP_200_OK: HealthResponseSerializer},
    tags=["system"],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_view(_request: Request) -> Response:
    """Return a lightweight application-health response."""
    return Response({"status": "ok"})
