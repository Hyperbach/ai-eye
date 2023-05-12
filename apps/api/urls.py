from django.urls import include, path, re_path

from rest_framework.routers import DefaultRouter

from .views import (
    CreateLogViewSet,
    PipelineCallAPIView,
    PipelineRetrieveArgumentsViewSet,
    PipelineRetrieveExecutionLogsViewSet,
    RetrieveLogAPIView,
)

app_name = "api"

router = DefaultRouter()

router.register(r"openai/(?P<endpoint>.+)", CreateLogViewSet, basename="openai")
router.register(
    "pipeline/args", PipelineRetrieveArgumentsViewSet, basename="pipeline_args"
)
router.register(
    "pipeline/logs", PipelineRetrieveExecutionLogsViewSet, basename="pipeline_logs"
)

urlpatterns = [
    path("", include(router.urls)),
    re_path(r"^cache/(?P<endpoint>.+)/$", RetrieveLogAPIView.as_view(), name="cache"),
    path("pipeline/call", PipelineCallAPIView.as_view(), name="pipeline_call"),
]
