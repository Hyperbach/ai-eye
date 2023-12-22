from django.utils.translation import gettext_lazy as _

import rest_framework.authentication
from core.enums import UserGroupType
from core.models import PublicToken
from rest_framework import exceptions


class AiEyeTokenAuthentication(rest_framework.authentication.TokenAuthentication):
    model = PublicToken
    keyword = "Bearer"

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)

        # token is "Public token"
        if not token.is_active:
            raise exceptions.AuthenticationFailed(_("Inactive token."))

        if not token.apikey.is_active:
            raise exceptions.AuthenticationFailed(_("Inactive related OpenAI token."))

        if not user.is_aieye_user:
            raise exceptions.AuthenticationFailed(
                _(f"Invalid user role, should be {UserGroupType.AIEYE_USERS}.")
            )

        return user, token
