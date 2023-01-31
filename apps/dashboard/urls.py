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
        "openaikeys/<int:pk>/update",
        views.OpenAIKeysUpdateView.as_view(),
        name="openaikeys_update",
    ),
    path(
        "openaikeys/<int:pk>/delete",
        views.OpenAIKeysDeleteView.as_view(),
        name="openaikeys_delete",
    ),
]
