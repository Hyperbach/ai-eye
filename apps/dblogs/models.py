from django.contrib.auth import get_user_model
from django.db import models

from core.models import PublicToken
from pipelines.models import PipelineSource

User = get_user_model()


class PipelineExecutionLog(models.Model):
    STATUS_CHOICES = (
        ("success", "Executed successfully"),
        ("error", "Errors"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    pipeline = models.ForeignKey(PipelineSource, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    apikey = models.ForeignKey(PublicToken, on_delete=models.CASCADE)
    parameters = models.JSONField()
    output = models.TextField()
    total_prompt_tokens = models.IntegerField()
    total_completion_tokens = models.IntegerField()
    total_tokens = models.IntegerField()
    total_prompt_cost = models.FloatField()
    total_completion_cost = models.FloatField()
    total_cost = models.FloatField()
    error = models.TextField()


class CallEntryLog(models.Model):
    FN_TYPE_CHOICES = (
        ("builtin", "Built-in"),
        ("prompt", "Prompt"),
    )

    fn_name = models.CharField(max_length=100)
    fn_type = models.CharField(max_length=10, choices=FN_TYPE_CHOICES)
    model = models.CharField(max_length=79, null=True)
    pipeline_execution_id = models.IntegerField()
    parameters = models.JSONField()
    output = models.TextField()
    full_response = models.TextField()
    prompt_tokens = models.IntegerField()
    completion_tokens = models.IntegerField()
    prompt_cost = models.FloatField()
    completion_cost = models.FloatField()
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(auto_now_add=True)
