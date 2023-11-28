from django.urls import path

from . import views
from .views import index, DocumentListView, DocumentCreateView, DocumentDetailView, \
    DocumentDeleteView, DocumentUpdateView

app_name = "dashboard"

urlpatterns = [
    path("", index, name="index"),
    path("users", views.UserListView.as_view(), name="users"),
    path("users/add", views.UserCreateView.as_view(), name="users_create"),
    path("openaikeys", views.OpenAIKeysListView.as_view(), name="openaikeys"),
    path(
        "openaikeys/add", views.OpenAIKeysCreateView.as_view(), name="openaikeys_create"
    ),
    path(
        "openaikeys/<int:pk>/update/",
        views.OpenAIKeysUpdateView.as_view(),
        name="openaikeys_update",
    ),
    path(
        "openaikeys/<int:pk>/delete/",
        views.OpenAIKeysDeleteView.as_view(),
        name="openaikeys_delete",
    ),
    path("publictokens", views.PublicTokensListView.as_view(), name="publictokens"),
    path(
        "publictokens/add",
        views.PublicTokensCreateView.as_view(),
        name="publictokens_create",
    ),
    path(
        "publictokens/<int:pk>/update/",
        views.PublicTokensUpdateView.as_view(),
        name="publictokens_update",
    ),
    path(
        "publictokens/<int:pk>/delete/",
        views.PublicTokensDeleteView.as_view(),
        name="publictokens_delete",
    ),
    path("caches", views.CachesListView.as_view(), name="caches"),
    path(
        "caches/<int:pk>/delete/",
        views.CachesDeleteView.as_view(),
        name="caches_delete",
    ),
    path(
        "caches/delete/",
        views.CachesDeleteAllView.as_view(),
        name="caches_delete_all",
    ),
    path("prompts", views.PromptListView.as_view(), name="prompts"),
    path("prompts/add", views.PromptCreateView.as_view(), name="prompt_create"),
    path(
        "prompts/<int:pk>/update/",
        views.PromptUpdateView.as_view(),
        name="prompt_update",
    ),
    path(
        "prompts/<int:pk>/delete/",
        views.PromptDeleteView.as_view(),
        name="prompt_delete",
    ),
    path("builtins", views.BuiltinFunctionListView.as_view(), name="builtins"),
    path(
        "builtins/sync",
        views.SyncBuiltinFunctionsAPIView.as_view(),
        name="builtin_sync",
    ),
    path(
        "builtins/<int:pk>/update/",
        views.BuiltinFunctionUpdateView.as_view(),
        name="builtin_update",
    ),
    path("pipelines", views.PipelineSourceListView.as_view(), name="pipelines"),
    path(
        "pipeline/executions",
        views.PipelineExecutionHistoryView.as_view(),
        name="pipelines_executions",
    ),
    path(
        "pipelines/<int:pk>/executions",
        views.PipelineDetailExecHistoryView.as_view(),
        name="pipeline_detail_exec_history",
    ),
    path(
        "pipelines/add",
        views.PipelineSourceCreateView.as_view(),
        name="pipeline_create",
    ),
    path(
        "pipelines/<int:pk>/update/",
        views.PipelineSourceUpdateView.as_view(),
        name="pipeline_update",
    ),
    path(
        "pipelines/<int:pk>/delete/",
        views.PipelineSourceDeleteView.as_view(),
        name="pipeline_delete",
    ),
    path(
        "pipelines/execute/",
        views.PipelineSourceExecuteView.as_view(),
        name="pipeline_execute",
    ),
    path(
        "pipelines/execute/<int:id>/",
        views.PipelineSourceExecuteView.as_view(),
        name="pipeline_execute",
    ),
    path("documents", DocumentListView.as_view(), name="document_list"),
    path("documents/add", DocumentCreateView.as_view(), name="document_create"),
    path("documents/<str:pk>/", DocumentDetailView.as_view(), name="document_detail"),
    path("documents/<str:pk>/delete", DocumentDeleteView.as_view(), name="document_delete"),
    path("documents/<str:pk>/update", DocumentUpdateView.as_view(), name="document_update"),

]
