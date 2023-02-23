from rest_framework import serializers

from .models import Log


class CacheHitResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = ["response", "cache_hit"]


# class GenericField(serializers.Field):
#     default_error_messages = {
#         "invalid": _("A valid value is required: str, int or float."),  # type: ignore
#     }
#
#     def to_internal_value(self, data):
#         if isinstance(data, (str, int, float)):
#             return data
#         self.fail("invalid")
#
#     def to_representation(self, value):
#         return value
#
#
# class PipelineCallSerializer(serializers.Serializer):
#     pipeline_id = serializers.IntegerField(required=True)
#     args = serializers.ListField(
#         child=serializers.ListField(child=GenericField()), required=True
#     )


class PipelineCallSerializer(serializers.Serializer):
    pipeline_id = serializers.IntegerField(required=True)
    args = serializers.DictField(child=serializers.CharField())
