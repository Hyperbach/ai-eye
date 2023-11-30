import datetime
import logging

from django.db.models import Max, Q
from django.http import Http404
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import OpenAIKey
from core.services.uploaders import DocumentUploader
from dblogs.models import CallEntryLog, PipelineExecutionLog
from pipelines.models import PipelineSource, Document
from pipelines.services.exceptions import PipelineException
from pipelines.services.pipeline_executor import PipelineExecutor
from pipelines.utils import find_first
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
    PipelineRetrieveExecutionLogsSerializer, DocumentCreationSerializer, )
from .services import OpenAICacheService

logger = logging.getLogger("console")


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


class PipelineCallAPIView(APIView):
    permission_classes = (
        permissions.IsAuthenticated,
        (AiEyeUserPermission | AiEyeAdminPermission),
    )
    authentication_classes = (AiEyeTokenAuthentication, SessionAuthentication)

    @staticmethod
    def retrieve_openaikey_for_aieyetokenauthenticated_user(request):
        public_token = request.auth
        return public_token.openaikey.key

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

    def get_openaikey(self, request, authenticator, validated_data):
        if isinstance(authenticator, AiEyeTokenAuthentication):
            return self.retrieve_openaikey_for_aieyetokenauthenticated_user(request)
        else:
            return self.retrieve_openaikey_for_session_authenticated_user(
                request, validated_data
            )

    def post(self, request, format=None):
        authenticator = find_first(
            lambda auth: auth.authenticate(request), request.authenticators
        )

        if isinstance(authenticator, AiEyeTokenAuthentication):
            serializer_class = PipelineCallSerializer
        else:
            serializer_class = PipelineCallWithOpenaiKeyId

        serializer = serializer_class(data=request.data)

        if serializer.is_valid():
            openaikey = self.get_openaikey(
                request, authenticator, serializer.validated_data
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
            pipeline_name = serializer.validated_data["pipeline_name"]
            try:
                pipeline_source_instance = PipelineSource.objects.get(
                    name=pipeline_name
                )
                p = PipelineExecutor(
                    pipeline_source_id=pipeline_source_instance.pk, user=request.user
                )
                arg_names = p.get_arg_names()
            except (PipelineSource.DoesNotExist, PipelineException) as exc:
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


class DocumentAPIView(APIView):
    permission_classes = (
        permissions.IsAuthenticated,
        (AiEyeUserPermission | AiEyeAdminPermission),
    )
    authentication_classes = (AiEyeTokenAuthentication,)

    http_method_names = [
        "post",
        "delete",
    ]

    @staticmethod
    def retrieve_openaikey_for_aieyetokenauthenticated_user(request):
        public_token = request.auth
        return public_token.openaikey.key

    def get_object(self, pk):
        try:
            return Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            raise Http404

    def delete(self, request, pk, format=None):
        instance = self.get_object(pk)
        openai_key = self.retrieve_openaikey_for_aieyetokenauthenticated_user(request)

        try:
            document_uploader = DocumentUploader(openai_key=openai_key)
            response = document_uploader.delete(instance.id)

            if response.deleted:
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({"error": "Failed to delete the file from OpenAI"},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"error": f"Failed to delete the file from OpenAI: {exc}"},
                            status=status.HTTP_400_BAD_REQUEST)
        finally:
            instance.delete()

    def post(self, request, format=None):
        serializer = DocumentCreationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        openai_key = self.retrieve_openaikey_for_aieyetokenauthenticated_user(request)

        uploaded_file = serializer.validated_data['file']
        original_file_name = uploaded_file.name
        document_uploader = DocumentUploader(openai_key=openai_key)

        try:
            response = document_uploader.upload_file_to_openai(uploaded_file=uploaded_file,
                                                               user_id=self.request.user.id)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            logger.debug(f"Response data from OpenAI API: {response}")

            document_instance = Document(
                id=response.id,
                object_type=response.object,
                bytes=response.bytes,
                filename=response.filename,
                original_filename=original_file_name,
                purpose=response.purpose,
                created_at=datetime.datetime.fromtimestamp(response.created_at),
                owner=self.request.user
            )
            document_instance.save()
            logger.info(f"Document object saved with ID: {document_instance.id}")

            return Response({
                "success": True,
                "document_id": document_instance.id,
            },
                status=status.HTTP_200_OK)
