from django.contrib import admin

from dblogs.models import CallEntryLog, PipelineExecutionLog


@admin.register(CallEntryLog)
class CallEntryLogAdmin(admin.ModelAdmin):
    pass


@admin.register(PipelineExecutionLog)
class PipelineExecutionLogAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "pipeline",
        "status",
        "apikey",
        "parameters",
        "output",
        "error",
        "start_date",
        "end_date",
    ]
