from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import CreateLogViewSet, RetrieveLogViewSet

app_name = "api"

router = DefaultRouter()

router.register(r"openai/(?P<endpoint>.+)", CreateLogViewSet, basename="openai")
router.register(r"cache/(?P<endpoint>.+)", RetrieveLogViewSet, basename="cache")

urlpatterns = [
    path("", include(router.urls)),
]
