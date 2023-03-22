from django.db.models import Max, Q

from core.models import OpenAIKey
from dblogs.models import CallEntryLog, PipelineExecutionLog
from pipelines.services.exceptions import PipelineException
from pipelines.services.pipeline_executor import PipelineExecutor
from pipelines.utils import find_first
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import AiEyeTokenAuthentication
from .models import Log
from .permissions import AiEyeAdminPermission, AiEyeUserPermission
from .serializers import (
    CacheHitResponseSerializer,
    CallEntryLogSerializer,
    PipelineCallSerializer,
    PipelineCallWithOpenaiKeyId,
    PipelineExecutionLogSerializer,
    PipelineRetrieveArgumentsCallSerializer,
    PipelineRetrieveExecutionLogsSerializer,
)
from .services import OpenAICacheService


class RetrieveLogAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated, AiEyeUserPermission)
    authentication_classes = (AiEyeTokenAuthentication,)
    serializer_class = CacheHitResponseSerializer

    def post(self, request, *args, **kwargs):
        parameters = request.data

        openai_cache_service = OpenAICacheService(
            endpoint=kwargs["endpoint"], parameters=parameters
        )
        comparator = openai_cache_service.create_logs_comparator()

        queryset = (
            Log.objects.filter(cache_hit=True)
            .filter(comparator)
            .distinct("response")
            .order_by("response", "-timestamp")
        )

        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CreateLogViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = (permissions.IsAuthenticated, AiEyeUserPermission)
    authentication_classes = (AiEyeTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        endpoint = kwargs["endpoint"]
        parameters = self.request.data

        public_token = request.auth
        openaikey = public_token.openaikey

        openai_cache_service = OpenAICacheService(
            endpoint=endpoint, parameters=parameters
        )
        new_log_instance = openai_cache_service.run(
            openaikey=openaikey, user=self.request.user
        )

        response_serializer = CacheHitResponseSerializer(instance=new_log_instance)
        return Response(data=response_serializer.data, status=status.HTTP_200_OK)


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

        openaikey_instance = OpenAIKey.objects.filter(
            Q(owner=request.user) | Q(users__in=[request.user]),
            pk=openaikey_id,
            is_active=True,
        ).first()

        if not openaikey_instance:
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
                p = PipelineExecutor(pipeline_source_id=pipeline_id, user=request.user)
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
                p = PipelineExecutor(pipeline_source_id=pipeline_id, user=request.user)
                arg_names = p.get_arg_names()
            except PipelineException as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"success": True, "response": arg_names})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PipelineRetrieveExecutionLogsViewSet(viewsets.ViewSet):
    permission_classes = (
        permissions.IsAuthenticated,
        (AiEyeUserPermission | AiEyeAdminPermission),
    )
    authentication_classes = (SessionAuthentication,)

    def create(self, request):
        serializer = PipelineRetrieveExecutionLogsSerializer(data=request.data)
        if serializer.is_valid():
            pipeline_id = serializer.validated_data["pipeline_id"]

            pipeline_execution_log_instance = (
                PipelineExecutionLog.objects.filter(
                    user=request.user,
                    pipeline_id=pipeline_id,
                )
                .annotate(max_start_date=Max("start_date"))
                .order_by("-max_start_date")
                .first()
            )

            if not pipeline_execution_log_instance:
                raise ValidationError("PipelineExecutionLog was not found")

            call_entries_logs = CallEntryLog.objects.filter(
                pipeline_execution_id=pipeline_execution_log_instance.pk
            ).order_by("id")

            pipeline_execution_log_serializer = PipelineExecutionLogSerializer(
                instance=pipeline_execution_log_instance
            )
            call_entries_log_serializer = CallEntryLogSerializer(
                instance=call_entries_logs, many=True
            )

            return Response(
                data={
                    "pipeline_execution": pipeline_execution_log_serializer.data,
                    "call_entries": call_entries_log_serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
