from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

import access.urls as access_urls
import api.urls as api_urls
import dashboard.urls as dashboard_urls

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include(access_urls, namespace="access")),
    path("dashboard/", include(dashboard_urls, namespace="dashboard")),
    path("api/", include(api_urls, namespace="api")),
    path("", RedirectView.as_view(pattern_name="access:login"), name="index"),
]

if settings.DEBUG:
    import debug_toolbar.urls as debug_toolbar_urls

    urlpatterns.append(path("__debug__/", include(debug_toolbar_urls)))

handler404 = "dashboard.views.handler404"
handler500 = "dashboard.views.handler500"
