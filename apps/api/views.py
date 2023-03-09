from django.db.models import Q

from core.models import OpenAIKey
from pipelines.services.exceptions import PipelineException
from pipelines.services.pipeline_executor import PipelineExecutor
from pipelines.utils import find_first
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .authentication import AiEyeTokenAuthentication
from .exceptions import OpenAIRequestException
from .mixins import PrepareParametersMixin
from .models import Log
from .permissions import AiEyeAdminPermission, AiEyeUserPermission
from .serializers import (
    CacheHitResponseSerializer,
    PipelineCallSerializer,
    PipelineCallWithOpenaiKeyId,
    PipelineRetrieveArgumentsCallSerializer,
)
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
                self.create_logs_comparator(self.prepare_parameters(parameters)),
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

        log_instance = self.get_log_instance(prepared_parameters)

        if log_instance is not None:
            response = log_instance.response
            cache_hit = True
        else:
            response = self.get_openai_response(openaikey, endpoint, parameters)
            cache_hit = False

        new_log_instance = self.create_log_instance(
            endpoint=endpoint,
            parameters=prepared_parameters,
            user=self.request.user,
            api_key=openaikey,
            response=response,
            cache_hit=cache_hit,
        )

        response_serializer = CacheHitResponseSerializer(instance=new_log_instance)
        return Response(data=response_serializer.data, status=status.HTTP_200_OK)

    def get_log_instance(self, prepared_parameters):
        return Log.objects.filter(
            self.create_logs_comparator(prepared_parameters),
        ).first()

    @staticmethod
    def create_log_instance(**kwargs):
        return Log.objects.create(**kwargs)

    @staticmethod
    def get_openai_response(openaikey, endpoint, parameters):
        try:
            openai_response = openai_request(
                openaikey=openaikey, endpoint=endpoint, parameters=parameters
            )
        except OpenAIRequestException as exc:
            raise exc
        else:
            return openai_response


class PipelineCallViewSet(viewsets.ViewSet):
    permission_classes = (
        permissions.IsAuthenticated,
        (AiEyeUserPermission | AiEyeAdminPermission),
    )
    authentication_classes = (AiEyeTokenAuthentication, SessionAuthentication)

    @staticmethod
    def retrieve_openaikey_for_aieyetokenauthenticated_user(request, _):
        public_token = request.auth
        return public_token.openaikey

    @staticmethod
    def retrieve_openaikey_for_session_authenticated_user(request, validated_data):
        openaikey_id = validated_data["openaikey_id"]

        try:
            openaikey_instance = OpenAIKey.objects.get(
                Q(owner=request.user) | Q(users__in=[request.user]),
                pk=openaikey_id,
                is_active=True,
            )
        except OpenAIKey.DoesNotExist:
            raise ValidationError("OpenAIKey not found")
        else:
            return openaikey_instance.key

    authentication_settings = {
        AiEyeTokenAuthentication: {
            "serializer": PipelineCallSerializer,
            "retrieve_openaikey_fn": retrieve_openaikey_for_aieyetokenauthenticated_user,
        },
        SessionAuthentication: {
            "serializer": PipelineCallWithOpenaiKeyId,
            "retrieve_openaikey_fn": retrieve_openaikey_for_session_authenticated_user,
        },
    }

    def create(self, request):
        authenticator = find_first(
            lambda auth: auth.authenticate(request), request.authenticators
        )

        helper_struct = self.authentication_settings[authenticator.__class__]
        serializer_class = helper_struct["serializer"]
        serializer = serializer_class(data=request.data)

        if serializer.is_valid():
            openaikey = helper_struct["retrieve_openaikey_fn"](
                request, serializer.validated_data
            )

            pipeline_id = serializer.validated_data["pipeline_id"]
            args = serializer.validated_data["args"]
            try:
                p = PipelineExecutor(pipeline_source_id=pipeline_id)
                result = p.exec(user_args=args, openaikey=openaikey)
            except PipelineException as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"success": True, "response": result})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PipelineRetrieveArgumentsViewSet(viewsets.ViewSet):
    permission_classes = (
        permissions.IsAuthenticated,
        (AiEyeUserPermission | AiEyeAdminPermission),
    )
    authentication_classes = (SessionAuthentication,)

    def list(self, request):
        serializer = PipelineRetrieveArgumentsCallSerializer(data=request.query_params)
        if serializer.is_valid():
            pipeline_id = serializer.validated_data["pipeline_id"]
            try:
                p = PipelineExecutor(pipeline_source_id=pipeline_id)
                arg_names = p.get_arg_names()
            except PipelineException as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"success": True, "response": arg_names})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
