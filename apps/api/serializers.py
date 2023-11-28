from dblogs.models import CallEntryLog, PipelineExecutionLog
from rest_framework import serializers

from pipelines.models import Document
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

    def create(self, validated_data):
        return Document.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.description = validated_data.get('description', instance.description)
        instance.save()
        return instance
