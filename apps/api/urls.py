from django.urls import include, path, re_path

from rest_framework import routers

from .views import CreateLogViewSet

app_name = "api"

router = routers.DefaultRouter()

urlpatterns = [
    path("", include(router.urls)),
    re_path(
        r"^openai/(?P<endpoint>.+)/$", CreateLogViewSet.as_view({"post": "create"})
    ),
]
