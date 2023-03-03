from rest_framework import serializers

from .models import Log


class CacheHitResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = ["response", "cache_hit"]


class PipelineCallSerializer(serializers.Serializer):
    pipeline_id = serializers.IntegerField(min_value=0, required=True)
    args = serializers.DictField(child=serializers.CharField())


class PipelineCallWithOpenaiKeyId(PipelineCallSerializer):
    openaikey_id = serializers.IntegerField(min_value=0, required=True)


class PipelineRetrieveArgumentsCallSerializer(serializers.Serializer):
    pipeline_id = serializers.IntegerField(min_value=0, required=True)
