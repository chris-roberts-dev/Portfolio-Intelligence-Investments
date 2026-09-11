from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from config.health import health_view

urlpatterns = [
    path("api/v1/health/", health_view, name="api-v1-health"),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="api-v1-schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="api-v1-schema"),
        name="api-v1-docs",
    ),
]
