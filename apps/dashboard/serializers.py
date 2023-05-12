from rest_framework import serializers


class BuiltinFunctionsSyncSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    deleted = serializers.ListField(child=serializers.CharField())
    created = serializers.ListField(child=serializers.CharField())
