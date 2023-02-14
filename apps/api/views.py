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
        endpoint = self.kwargs["endpoint"]
        parameters, parameters_stringified = self.prepare_parameters(
            self.request.query_params
        )

        return (
            Log.objects.filter(
                cache_hit=True,
                endpoint=endpoint,
                parameters=parameters_stringified,
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
        parameters, parameters_stringified = self.prepare_parameters(self.request.data)

        public_token = request.auth
        openaikey = public_token.openaikey

        log_instance = Log.objects.filter(
            endpoint=endpoint,
            parameters=parameters_stringified,
        ).first()

        log_instance_kwargs = dict(
            endpoint=endpoint,
            parameters=parameters_stringified,
            user=self.request.user,
            api_key=openaikey,
        )

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

        log_instance_kwargs.update({"response": response, "cache_hit": cache_hit})

        new_log_instance = Log.objects.create(**log_instance_kwargs)

        response_serializer = CacheHitResponseSerializer(instance=new_log_instance)
        return Response(data=response_serializer.data, status=status.HTTP_200_OK)
