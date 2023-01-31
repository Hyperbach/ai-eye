from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="dashboard:users"), name="index"),
    path("users", views.UserListView.as_view(), name="users"),
    path("users/add", views.UserCreateView.as_view(), name="users_create"),
]
