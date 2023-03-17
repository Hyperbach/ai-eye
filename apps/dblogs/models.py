from django.contrib.auth import get_user_model
from django.db import models

from core.models import OpenAIKey
from pipelines.models import PipelineSource

User = get_user_model()


class PipelineExecution(models.Model):
    STATUS_CHOICES = (
        ("success", "Executed successfully"),
        ("error", "Errors"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    pipeline = models.ForeignKey(PipelineSource, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    openai_key = models.ForeignKey(OpenAIKey, on_delete=models.CASCADE)
    parameters = models.JSONField()
    output = models.TextField()
    error = models.TextField()


class LogEntry(models.Model):
    FN_TYPE_CHOICES = (
        ("builtin", "Built-in"),
        ("prompt", "Prompt"),
    )

    fn_name = models.CharField(max_length=100)
    fn_type = models.CharField(max_length=10, choices=FN_TYPE_CHOICES)
    pipeline_execution_id = models.IntegerField()
    parameters = models.JSONField()
