from django.utils.translation import gettext_lazy as _

import rest_framework.authentication
from core.models import PublicToken
from rest_framework import exceptions


class AiEyeTokenAuthentication(rest_framework.authentication.TokenAuthentication):
    model = PublicToken
    keyword = "Bearer"

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)

        if not token.is_active:
            raise exceptions.AuthenticationFailed(_("Inactive token."))

        return user, token
