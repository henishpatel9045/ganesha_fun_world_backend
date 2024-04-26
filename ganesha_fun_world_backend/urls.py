from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
import os

schema_view = get_schema_view(
    openapi.Info(
        title="Ganesha Management System API",
        default_version="v1",
        contact=openapi.Contact(email="henishpatel9045@gmail.com"),
    ),
    public=False,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "swagger<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"
    ),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("bookings/", include("bookings.urls")),
]

if os.environ.get("ENVIRONMENT", "test") == "test":
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
