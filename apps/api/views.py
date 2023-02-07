from http import HTTPStatus

from core.models import OpenAIKey
from rest_framework import permissions, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .authentication import AiEyeTokenAuthentication
from .exceptions import OpenAIRequestException
from .models import Log
from .permissions import AiEyeUserPermission
from .serializers import CacheHitResponseSerializer
from .services import openai_request


class CreateLogViewSet(viewsets.ViewSet):
    permission_classes = (permissions.IsAuthenticated, AiEyeUserPermission)
    authentication_classes = (AiEyeTokenAuthentication,)

    ALLOWED_OPENAI_ENDPOINTS = [
        "v1/completions",
        "v1/edits",
    ]

    def create(self, request, *args, **kwargs):
        endpoint = kwargs.pop("endpoint")
        if endpoint not in self.ALLOWED_OPENAI_ENDPOINTS:
            raise ValidationError("Invalid data")

        if not request.data:
            raise ValidationError("Invalid data")
        if "api_type" not in request.data or type(request.data["api_type"]) is not str:
            raise ValidationError("Invalid data")

        parameters = {k: v for k, v in request.data.items() if k != "api_type"}
        parameters_stringified = Log.stringify_parameters(parameters)

        public_token = request.auth
        openaikey = public_token.openaikey
        openai_key_instance = OpenAIKey.objects.get(key=openaikey)

        log_instance = Log.objects.filter(
            api_type=request.data["api_type"],
            endpoint=endpoint,
            parameters=parameters_stringified,
        ).first()

        if log_instance is not None:
            new_log_instance = Log.objects.create(
                api_type=request.data["api_type"],
                endpoint=endpoint,
                parameters=parameters_stringified,
                user=self.request.user,
                api_key=openai_key_instance,
                response=log_instance.response,
                cache_hit=True,
            )
        else:
            try:
                response = openai_request(
                    openaikey=openaikey, endpoint=endpoint, parameters=parameters
                )
            except OpenAIRequestException as exc:
                raise exc
            else:
                new_log_instance = Log.objects.create(
                    api_type=request.data["api_type"],
                    endpoint=endpoint,
                    parameters=parameters_stringified,
                    user=self.request.user,
                    api_key=openai_key_instance,
                    response=response,
                    cache_hit=True,
                )

        response_serializer = CacheHitResponseSerializer(instance=new_log_instance)
        return Response(data=response_serializer.data, status=HTTPStatus.OK)
