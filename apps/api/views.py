from pipelines.services.exceptions import PipelineException
from pipelines.services.pipeline_executor import PipelineExecutor
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.response import Response

from .authentication import AiEyeTokenAuthentication
from .exceptions import OpenAIRequestException
from .mixins import PrepareParametersMixin
from .models import Log
from .permissions import AiEyeUserPermission
from .serializers import CacheHitResponseSerializer, PipelineCallSerializer
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
    permission_classes = (permissions.IsAuthenticated, AiEyeUserPermission)
    authentication_classes = (AiEyeTokenAuthentication,)

    def create(self, request):
        serializer = PipelineCallSerializer(data=request.data)
        if serializer.is_valid():
            public_token = request.auth
            openaikey = public_token.openaikey

            pipeline_id = serializer.validated_data["pipeline_id"]
            args = serializer.validated_data["args"]
            try:
                p = PipelineExecutor(
                    pipeline_source_id=pipeline_id, openaikey=openaikey
                )
                result = p.exec(user_args=args)
            except PipelineException as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"success": True, "response": result})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
