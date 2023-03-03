from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import (
    CreateLogViewSet,
    PipelineCallViewSet,
    PipelineRetrieveArgumentsViewSet,
    RetrieveLogViewSet,
)

app_name = "api"

router = DefaultRouter()

router.register(r"openai/(?P<endpoint>.+)", CreateLogViewSet, basename="openai")
router.register(r"cache/(?P<endpoint>.+)", RetrieveLogViewSet, basename="cache")
router.register("pipeline/call", PipelineCallViewSet, basename="pipeline")
router.register(
    "pipeline/args", PipelineRetrieveArgumentsViewSet, basename="pipeline_args"
)

urlpatterns = [
    path("", include(router.urls)),
]
