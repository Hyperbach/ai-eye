from rest_framework import mixins, permissions, status, viewsets
from rest_framework.response import Response

from .authentication import AiEyeTokenAuthentication
from .exceptions import OpenAIRequestException
from .mixins import PrepareParametersMixin
from .models import Log
from .permissions import AiEyeUserPermission
from .serializers import CacheHitResponseSerializer
from .services import openai_request


class RetrieveLogViewSet(
    viewsets.GenericViewSet, mixins.ListModelMixin, PrepareParametersMixin
):
    permission_classes = (permissions.IsAuthenticated, AiEyeUserPermission)
    authentication_classes = (AiEyeTokenAuthentication,)
    serializer_class = CacheHitResponseSerializer

    def get_queryset(self):
        parameters = self.request.query_params
        return (
            Log.objects.filter(cache_hit=True)
            .filter(
                self.comparator(self.prepare_parameters(parameters)),
            )
            .distinct("response")
            .order_by("response", "-timestamp")
        )


class CreateLogViewSet(
    mixins.CreateModelMixin, viewsets.GenericViewSet, PrepareParametersMixin
):
    permission_classes = (permissions.IsAuthenticated, AiEyeUserPermission)
    authentication_classes = (AiEyeTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        endpoint = kwargs["endpoint"]
        parameters = self.request.data
        prepared_parameters = self.prepare_parameters(parameters)

        public_token = request.auth
        openaikey = public_token.openaikey

        log_instance = Log.objects.filter(
            self.comparator(prepared_parameters),
        ).first()

        if log_instance is not None:
            response = log_instance.response
            cache_hit = True
        else:
            try:
                openai_response = openai_request(
                    openaikey=openaikey.key, endpoint=endpoint, parameters=parameters
                )
            except OpenAIRequestException as exc:
                raise exc
            else:
                response = openai_response
                cache_hit = False

        new_log_instance = Log.objects.create(
            endpoint=endpoint,
            parameters=prepared_parameters,
            user=self.request.user,
            api_key=openaikey,
            response=response,
            cache_hit=cache_hit,
        )

        response_serializer = CacheHitResponseSerializer(instance=new_log_instance)
        return Response(data=response_serializer.data, status=status.HTTP_200_OK)
