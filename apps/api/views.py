from django.contrib.auth import get_user_model

from core.models import PublicToken
from rest_framework import permissions, viewsets

from .authentication import AiEyeTokenAuthentication
from .serializers import UserSerializer

UserModel = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """

    queryset = UserModel.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = (
        AiEyeTokenAuthentication,
    )  # request.auth is PublicToken from the headers

    def list(self, request, *args, **kwargs):

        public_token: PublicToken = request.auth
        openaikey = public_token.openaikey

        print(
            f"user: {request.user}, public_token: {public_token}, openaikey: {openaikey}"
        )
        return super().list(request, args, kwargs)
