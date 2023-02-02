from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("access.urls", namespace="access")),
    path("dashboard/", include("dashboard.urls", namespace="dashboard")),
    path("api/", include("api.urls")),
]

if settings.DEBUG:
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]

handler404 = "dashboard.views.handler404"
handler500 = "dashboard.views.handler500"
