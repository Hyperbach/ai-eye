import datetime
import logging

from django.db.models import Max, Q
from django.http import Http404

from core.models import OpenAIKey
from core.services.uploaders import AssistantUploader, DocumentUploader
from dblogs.models import CallEntryLog, PipelineExecutionLog
from pipelines.models import Assistant, Document, PipelineSource
from pipelines.services.exceptions import PipelineException
from pipelines.services.pipeline_executor import PipelineExecutor
from pipelines.utils import find_first
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import AiEyeTokenAuthentication
from .models import Log
from .permissions import AiEyeAdminPermission, AiEyeUserPermission
from .serializers import (
    AssistantCreationSerializer,
    CacheHitResponseSerializer,
    CallEntryLogSerializer,
    DocumentCreationSerializer,
    PipelineCallSerializer,
    PipelineCallWithOpenaiKeyId,
    PipelineExecutionLogSerializer,
    PipelineRetrieveArgumentsCallSerializer,
    PipelineRetrieveExecutionLogsSerializer,
)
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


class PipelineExecutionLogsViewSet(viewsets.ViewSet):
    permission_classes = (
        permissions.IsAuthenticated,
        (AiEyeUserPermission | AiEyeAdminPermission),
    )
    authentication_classes = (SessionAuthentication,)

    def retrieve(self, request, pk=None):  # Ensure 'pk' is accepted as an argument
        if pk is None:
            return Response(
                {"error": "An execution ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            pipeline_execution_log_instance = PipelineExecutionLog.objects.get(
                pk=pk, user=request.user
            )
        except PipelineExecutionLog.DoesNotExist:
            raise NotFound(
                "A PipelineExecutionLog with the provided ID does not exist."
            )

        call_entries_logs = CallEntryLog.objects.filter(
            pipeline_execution_id=pipeline_execution_log_instance.pk
        ).order_by("id")
        call_entries_log_serializer = CallEntryLogSerializer(
            instance=call_entries_logs, many=True
        )

        return Response(
            {"execution_id": pk, "call_entries": call_entries_log_serializer.data},
            status=status.HTTP_200_OK,
        )


class AssistantAPIView(APIView):
    permission_classes = (
        permissions.IsAuthenticated,
        (AiEyeUserPermission | AiEyeAdminPermission),
    )
    authentication_classes = (AiEyeTokenAuthentication,)

    http_method_names = [
        "post",
        "patch",
    ]

    @staticmethod
    def retrieve_openaikey_for_aieyetokenauthenticated_user(request):
        public_token = request.auth
        return public_token.openaikey.key

    def get_object(self, pk):
        try:
            return Assistant.objects.get(pk=pk)
        except Assistant.DoesNotExist:
            raise Http404

    def patch(self, request, pk, format=None):
        logger.info("Processing assistant patch submission.")

        existing_instance = self.get_object(pk)

        serializer = AssistantCreationSerializer(
            instance=existing_instance, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        instance_changed = False
        model_fields_changed = False

        model_fields_to_compare = [
            "name",
            "description",
            "model",
            "instructions",
            "metadata",
        ]
        if not all(
            serializer.validated_data.get(field) == getattr(existing_instance, field)
            for field in model_fields_to_compare
        ):
            model_fields_changed = True

        if model_fields_changed:
            existing_instance = serializer.save()
            instance_changed = True
        else:
            existing_instance_file_ids = set(
                existing_instance.files.values_list("id", flat=True)
            )
            new_file_ids = set(
                doc.id for doc in serializer.validated_data.get("files", [])
            )

            if existing_instance_file_ids != new_file_ids:
                instance_changed = True
                if new_file_ids:
                    document_instances = Document.objects.filter(id__in=new_file_ids)
                    existing_instance.files.set(document_instances)
                else:
                    existing_instance.files.set.clear()

        if instance_changed:
            openai_key = self.retrieve_openaikey_for_aieyetokenauthenticated_user(
                request
            )

            # Prepare the payload for updating the assistant in OpenAI
            update_payload = {
                "model": existing_instance.model,
                "instructions": existing_instance.instructions,
                "metadata": existing_instance.metadata,
                "name": existing_instance.prefixed_name,
                "file_ids": [doc.id for doc in existing_instance.files.all()],
            }

            try:
                response = AssistantUploader.update_assistant_in_openai(
                    openai_key=openai_key,
                    openai_id=existing_instance.openai_id,
                    update_payload=update_payload,
                )
            except Exception as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                logger.info("Assistant updated in OpenAI: " + str(response))

        return Response(
            {
                "success": True,
                "assistant_id": existing_instance.id,
                "was_changed": instance_changed,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, format=None):
        logger.info("Processing assistant create submission.")

        serializer = AssistantCreationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        openai_key = self.retrieve_openaikey_for_aieyetokenauthenticated_user(request)

        unprefixed_name = serializer.validated_data.get("name", "")

        # Generate new assistant name with prefix
        prefix = f"1g_{self.request.user.id}_"
        prefixed_name = prefix + unprefixed_name

        openai_file_ids = [doc.id for doc in serializer.validated_data.get("files", [])]

        try:
            response = AssistantUploader.create_assistant_in_openai(
                openai_key=openai_key,
                prefixed_name=prefixed_name,
                uploaded_data=serializer.validated_data,
                openai_file_ids=openai_file_ids,
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            logger.debug(f"Response data from OpenAI API: {response}")

            assistance_instance = serializer.save(
                prefixed_name=prefixed_name,
                openai_id=openai_key,
                created_at=datetime.datetime.fromtimestamp(response.created_at),
                owner=self.request.user,
            )

            logger.info(f"Assistant object saved with ID: {assistance_instance.id}")

            return Response(
                {
                    "success": True,
                    "assistant_id": assistance_instance.id,
                },
                status=status.HTTP_200_OK,
            )


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
            response = DocumentUploader.delete(
                openai_key=openai_key, object_id=instance.id
            )

            if response.deleted:
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(
                    {"error": "Failed to delete the file from OpenAI"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as exc:
            return Response(
                {"error": f"Failed to delete the file from OpenAI: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        finally:
            instance.delete()

    def post(self, request, format=None):
        serializer = DocumentCreationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        openai_key = self.retrieve_openaikey_for_aieyetokenauthenticated_user(request)

        uploaded_file = serializer.validated_data["file"]
        original_file_name = uploaded_file.name

        try:
            response = DocumentUploader.upload_file_to_openai(
                openai_key=openai_key,
                uploaded_file=uploaded_file,
                user_id=self.request.user.id,
            )
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
                owner=self.request.user,
            )
            document_instance.save()
            logger.info(f"Document object saved with ID: {document_instance.id}")

            return Response(
                {
                    "success": True,
                    "document_id": document_instance.id,
                },
                status=status.HTTP_200_OK,
            )
