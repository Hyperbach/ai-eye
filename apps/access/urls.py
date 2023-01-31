from django.contrib.auth.views import LogoutView
from django.urls import path

from configs import settings

from .views import LoginFormView

app_name = "access"

urlpatterns = [
    path("login", LoginFormView.as_view(), name="login"),
    path(
        "logout",
        LogoutView.as_view(next_page=settings.LOGOUT_REDIRECT_URL),
        name="logout",
    ),
]
