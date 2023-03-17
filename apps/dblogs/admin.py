from django.contrib import admin

from dblogs.models import LogEntry, PipelineExecution


@admin.register(LogEntry)
class LogMessageAdmin(admin.ModelAdmin):
    pass


@admin.register(PipelineExecution)
class LogPipelineExecutionAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "pipeline",
        "status",
        "openai_key",
        "parameters",
        "output",
        "error",
        "start_date",
        "end_date",
    ]
