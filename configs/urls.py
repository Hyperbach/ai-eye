from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("access.urls", namespace="access")),
    path("dashboard/", include("dashboard.urls", namespace="dashboard")),
]
