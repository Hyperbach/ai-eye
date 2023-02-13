from rest_framework import serializers

from .models import Log


class CacheHitResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = ["response", "cache_hit"]
