from rest_framework import serializers

from dblogs.models import CallEntryLog, PipelineExecutionLog
from pipelines.models import Document, Assistant
from .models import Log


class CacheHitResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = ["response", "cache_hit"]


class PipelineCallSerializer(serializers.Serializer):
    pipeline_id = serializers.IntegerField(min_value=0, required=True)
    args = serializers.JSONField(required=True)


class PipelineCallWithOpenaiKeyId(PipelineCallSerializer):
    openaikey_id = serializers.IntegerField(min_value=0, required=True)


class PipelineRetrieveArgumentsCallSerializer(serializers.Serializer):
    pipeline_name = serializers.CharField(required=True)


class PipelineRetrieveExecutionLogsSerializer(serializers.Serializer):
    pipeline_id = serializers.IntegerField(min_value=0, required=True)


class PipelineExecutionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PipelineExecutionLog
        fields = "__all__"


class CallEntryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallEntryLog
        fields = "__all__"


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = '__all__'

    def update(self, instance, validated_data):
        instance.save(update_fields=["description"])
        return instance


class AssistantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assistant

    fields = "__all__"
