from django.contrib import admin
from django.urls import include, path

from api.urls import urlpatterns as api_urls

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("access.urls", namespace="access")),
    path("dashboard/", include("dashboard.urls", namespace="dashboard")),
]

urlpatterns += api_urls
