from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="dashboard:users"), name="index"),
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
]
