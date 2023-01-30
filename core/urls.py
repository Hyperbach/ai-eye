from django.conf import settings
from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views
from .views import index_view

app_name = 'core'

urlpatterns = [
    path('', index_view, name='home'),
    path('auth/login', views.LoginFormView.as_view(), name="login"),
    path('auth/logout', LogoutView.as_view(next_page=settings.LOGOUT_REDIRECT_URL), name='logout'),
]
