from django.urls import include, path, re_path

from rest_framework.routers import DefaultRouter

from .views import (
    CreateLogViewSet,
    PipelineCallViewSet,
    PipelineRetrieveArgumentsViewSet,
    PipelineRetrieveExecutionLogsViewSet,
    RetrieveLogAPIView,
)

app_name = "api"

router = DefaultRouter()

router.register(r"openai/(?P<endpoint>.+)", CreateLogViewSet, basename="openai")
router.register("pipeline/call", PipelineCallViewSet, basename="pipeline")
router.register(
    "pipeline/args", PipelineRetrieveArgumentsViewSet, basename="pipeline_args"
)
router.register(
    "pipeline/logs", PipelineRetrieveExecutionLogsViewSet, basename="pipeline_logs"
)

urlpatterns = [
    path("", include(router.urls)),
    re_path(r"^cache/(?P<endpoint>.+)/$", RetrieveLogAPIView.as_view()),
]
