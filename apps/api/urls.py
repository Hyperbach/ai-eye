from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from .views import (
    PipelineCallAPIView,
    PipelineRetrieveArgumentsViewSet,
    PipelineRetrieveExecutionLogsViewSet,
    RetrieveLogAPIView,
    PipelineExecutionLogsViewSet,
    DocumentAPIView, AssistantAPIView,
)

app_name = "api"

router = DefaultRouter()
router.register(
    "pipeline/args", PipelineRetrieveArgumentsViewSet, basename="pipeline_args"
)
router.register(
    "pipeline/logs", PipelineRetrieveExecutionLogsViewSet, basename="pipeline_logs"
),
router.register(
    "execution", PipelineExecutionLogsViewSet, basename="execution"
)

urlpatterns = [
    path("", include(router.urls)),
    re_path(r"^cache/(?P<endpoint>.+)/$", RetrieveLogAPIView.as_view(), name="cache"),
    path("pipeline/call", PipelineCallAPIView.as_view(), name="pipeline_call"),
    path("documents/", DocumentAPIView.as_view(), name="document_create"),
    path("documents/<str:pk>/", DocumentAPIView.as_view(), name="document_delete"),
    path("assistants/", AssistantAPIView.as_view(), name="assistant_create"),
    path("assistants/<str:pk>/",  AssistantAPIView.as_view(), name="assistant_update"),
]
