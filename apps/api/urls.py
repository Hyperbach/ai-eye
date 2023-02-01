from django.conf import settings
from django.urls import include, path

from api import views
from rest_framework import routers

# TODO:
router = routers.DefaultRouter()
router.register(r"users", views.UserViewSet)

urlpatterns = [
    path("api/", include(router.urls)),
]

if settings.DEBUG:
    urlpatterns.append(
        path("api-auth/", include("rest_framework.urls", namespace="rest_framework"))
    )
