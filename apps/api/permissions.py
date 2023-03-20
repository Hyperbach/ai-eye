from rest_framework.permissions import BasePermission


class AiEyeUserPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_aieye_user
